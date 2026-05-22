from __future__ import annotations

import argparse
import gc
import os
import sys
from pathlib import Path
from typing import Optional, Tuple

sys.path.insert(0, str(Path.cwd()))

import torch
import trimesh
from tqdm import tqdm
from transformers import CLIPTextModelWithProjection, CLIPTokenizerFast

from cube3d.inference.logits_postprocesses import process_logits
from cube3d.inference.utils import load_config, load_model_weights, normalize_bbox, parse_structured
from cube3d.model.autoencoder.one_d_autoencoder import OneDAutoEncoder
from cube3d.model.gpt.dual_stream_roformer import DualStreamRoformer


def select_device(force_cpu: bool = False) -> torch.device:
    if force_cpu:
        return torch.device("cpu")
    if torch.cuda.is_available():
        return torch.device("cuda")
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def clear_gpu() -> None:
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.ipc_collect()


class LowVRAMCubeEngine:
    def __init__(
        self,
        config_path: str,
        gpt_ckpt_path: str,
        shape_ckpt_path: str,
        device: torch.device,
        dtype: torch.dtype,
    ) -> None:
        self.cfg = load_config(config_path)
        self.device = device
        self.dtype = dtype
        self.shape_ckpt_path = shape_ckpt_path

        print("Loading GPT model on target device...")
        self.gpt_model = DualStreamRoformer(parse_structured(DualStreamRoformer.Config, self.cfg.gpt_model))
        load_model_weights(self.gpt_model, gpt_ckpt_path)
        self.gpt_model = self.gpt_model.eval().to(device=self.device, dtype=self.dtype)

        print("Loading shape tokenizer on CPU for codebook transfer...")
        shape_model_cpu = OneDAutoEncoder(parse_structured(OneDAutoEncoder.Config, self.cfg.shape_model))
        load_model_weights(shape_model_cpu, shape_ckpt_path)
        shape_model_cpu = shape_model_cpu.eval()

        with torch.no_grad():
            codebook = shape_model_cpu.bottleneck.block.get_codebook().to(self.device, dtype=self.dtype)
            codebook = self.gpt_model.shape_proj(codebook).detach()
            self.gpt_model.transformer.wte.weight.data[: codebook.shape[0]] = codebook
        self.max_new_tokens = shape_model_cpu.cfg.num_encoder_latents
        self.shape_cfg = shape_model_cpu.cfg
        del shape_model_cpu
        clear_gpu()

        print("Loading CLIP text encoder on CPU...")
        self.text_model = CLIPTextModelWithProjection.from_pretrained(
            self.cfg.text_model_pretrained_model_name_or_path,
            force_download=False,
        ).eval()
        self.text_tokenizer = CLIPTokenizerFast.from_pretrained(self.cfg.text_model_pretrained_model_name_or_path)
        self.min_id = 0
        self.max_id = self.shape_cfg.num_codes

    @torch.inference_mode()
    def run_clip_cpu(self, prompts: list[str]) -> torch.Tensor:
        text_inputs = self.text_tokenizer(
            prompts,
            max_length=self.text_tokenizer.model_max_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )
        with torch.no_grad():
            encoded = self.text_model(**text_inputs)
            embed = encoded.text_embeds.unsqueeze(1) if self.gpt_model.cfg.use_pooled_text_embed else encoded.last_hidden_state
        embed = embed.to(self.device, dtype=self.dtype)
        with torch.autocast(self.device.type, dtype=self.dtype, enabled=self.device.type != "cpu"):
            return self.gpt_model.encode_text(embed)

    @torch.inference_mode()
    def prepare_conditions_with_bbox(
        self,
        cond: torch.Tensor,
        bounding_box_tensor: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        if not hasattr(self.gpt_model, "bbox_proj"):
            return cond
        if bounding_box_tensor is None:
            bounding_box_tensor = torch.zeros((cond.shape[0], 3), dtype=cond.dtype, device=self.device)
        bbox_emb = self.gpt_model.bbox_proj(bounding_box_tensor).unsqueeze(dim=1)
        return torch.cat([cond, bbox_emb], dim=1)

    @torch.inference_mode()
    def generate_tokens(
        self,
        prompt: str,
        guidance_scale: float,
        use_kv_cache: bool,
        top_p: float | None,
        bounding_box_xyz: Optional[Tuple[float, float, float]],
    ) -> torch.Tensor:
        prompt_embeds = self.run_clip_cpu([prompt])
        with torch.autocast(self.device.type, dtype=self.dtype, enabled=self.device.type != "cpu"):
            embed = self.gpt_model.encode_token(
                torch.full((1, 1), fill_value=self.gpt_model.shape_bos_id, dtype=torch.long, device=self.device)
            )

        cond_bbox = torch.atleast_2d(torch.tensor(bounding_box_xyz, device=self.device, dtype=prompt_embeds.dtype)) if bounding_box_xyz else None
        cond = self.prepare_conditions_with_bbox(prompt_embeds, cond_bbox)
        if guidance_scale > 0.0:
            print("Classifier-free guidance is enabled; this uses more VRAM.")
            uncond_embeds = self.run_clip_cpu([""])
            uncond = self.prepare_conditions_with_bbox(uncond_embeds, torch.zeros_like(cond_bbox) if cond_bbox is not None else None)
            cond = torch.cat([cond, uncond], dim=0)
            embed = torch.cat([embed, embed], dim=0)

        output_ids = []
        batch_size, input_seq_len, dim = embed.shape
        embed_buffer = torch.zeros(
            (batch_size, input_seq_len + self.max_new_tokens, dim),
            dtype=embed.dtype,
            device=embed.device,
        )
        embed_buffer[:, :input_seq_len, :].copy_(embed)
        kv_cache = None
        if use_kv_cache:
            kv_cache = self.gpt_model.init_kv_cache(
                batch_size,
                cond.shape[1],
                self.max_new_tokens + 1,
                self.dtype,
                embed.device,
            )

        with torch.autocast(self.device.type, dtype=self.dtype, enabled=self.device.type != "cpu"):
            for i in tqdm(range(self.max_new_tokens), desc="generating"):
                curr_pos_id = torch.tensor([i], dtype=torch.long, device=embed.device)
                logits = self.gpt_model(
                    embed_buffer,
                    cond,
                    kv_cache=kv_cache,
                    curr_pos_id=curr_pos_id if use_kv_cache else None,
                    decode=(i > 0) if use_kv_cache else False,
                )
                logits = logits[:, 0, ...] if use_kv_cache else logits[:, i, ...]
                logits = logits[..., self.min_id : self.max_id]
                if guidance_scale > 0.0:
                    logits, uncond_logits = logits.float().chunk(2, dim=0)
                    gamma = guidance_scale * (self.max_new_tokens - i) / self.max_new_tokens
                    logits = (1 + gamma) * logits - gamma * uncond_logits
                next_id = process_logits(logits, top_p=top_p)
                output_ids.append(next_id)
                next_embed = self.gpt_model.encode_token(next_id)
                if guidance_scale > 0.0:
                    next_embed = torch.cat([next_embed, next_embed], dim=0)
                embed_buffer[:, i + input_seq_len, :].copy_(next_embed.squeeze(1))

        return torch.cat(output_ids, dim=1)

    def unload_gpt(self) -> None:
        del self.gpt_model
        del self.text_model
        del self.text_tokenizer
        clear_gpu()

    @torch.inference_mode()
    def decode_shape(self, output_ids: torch.Tensor, resolution_base: float, chunk_size: int):
        print("Loading shape decoder on target device...")
        shape_model = OneDAutoEncoder(parse_structured(OneDAutoEncoder.Config, self.cfg.shape_model))
        load_model_weights(shape_model, self.shape_ckpt_path)
        shape_model = shape_model.eval().to(device=self.device, dtype=self.dtype)
        shape_ids = output_ids[:, : shape_model.cfg.num_encoder_latents, ...].clamp_(0, shape_model.cfg.num_codes - 1)
        shape_ids = shape_ids.view(-1, shape_model.cfg.num_encoder_latents).to(self.device)
        with torch.autocast(self.device.type, dtype=self.dtype, enabled=self.device.type != "cpu"):
            latents = shape_model.decode_indices(shape_ids)
            mesh_v_f, _ = shape_model.extract_geometry(
                latents,
                resolution_base=resolution_base,
                chunk_size=chunk_size,
                use_warp=self.device.type == "cuda",
            )
        del shape_model
        clear_gpu()
        return mesh_v_f


def save_obj(vertices, faces, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    mesh = trimesh.Trimesh(vertices, faces, process=False)
    mesh.export(output_path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CubeLite low-VRAM Cube 3D generator")
    parser.add_argument("--config-path", required=True)
    parser.add_argument("--gpt-ckpt-path", required=True)
    parser.add_argument("--shape-ckpt-path", required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--output-name", default="output")
    parser.add_argument("--resolution-base", type=float, default=4.0)
    parser.add_argument("--chunk-size", type=int, default=20000)
    parser.add_argument("--guidance-scale", type=float, default=0.0)
    parser.add_argument("--top-p", type=float, default=None)
    parser.add_argument("--bounding-box-xyz", nargs=3, type=float, default=None)
    parser.add_argument("--use-kv-cache", action="store_true")
    parser.add_argument("--force-cpu", action="store_true")
    parser.add_argument("--dtype", choices=["bfloat16", "float16", "float32"], default="bfloat16")
    return parser.parse_args()


def main() -> None:
    os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
    args = parse_args()
    device = select_device(force_cpu=args.force_cpu)
    dtype = {"bfloat16": torch.bfloat16, "float16": torch.float16, "float32": torch.float32}[args.dtype]
    if device.type == "cpu":
        dtype = torch.float32
    bbox = tuple(args.bounding_box_xyz) if args.bounding_box_xyz else None
    if bbox is not None:
        bbox = tuple(normalize_bbox(bbox))
    top_p = args.top_p if args.top_p and args.top_p > 0 else None

    print(f"CubeLite low-VRAM generator using device={device}, dtype={dtype}, guidance_scale={args.guidance_scale}, top_p={top_p}, kv_cache={args.use_kv_cache}")
    engine = LowVRAMCubeEngine(args.config_path, args.gpt_ckpt_path, args.shape_ckpt_path, device, dtype)
    output_ids = engine.generate_tokens(args.prompt, args.guidance_scale, args.use_kv_cache, top_p, bbox)
    output_ids_cpu = output_ids.detach().cpu()
    engine.unload_gpt()
    mesh_v_f = engine.decode_shape(output_ids_cpu.to(device), args.resolution_base, args.chunk_size)
    vertices, faces = mesh_v_f[0][0], mesh_v_f[0][1]
    obj_path = Path(args.output_dir) / f"{args.output_name}.obj"
    save_obj(vertices, faces, obj_path)
    print(f"Generated mesh for {args.prompt} at `{obj_path}`")


if __name__ == "__main__":
    main()
