from __future__ import annotations

import json
from pathlib import Path

from app.benchmark.benchmark_prompts import BENCHMARK_PROMPTS
from app.benchmark.benchmark_runner import run_benchmark, run_single_pipeline
from app.config import (
    BENCHMARKS_DIR,
    EXPORTS_DIR,
    OUTPUTS_DIR,
    REPORTS_DIR,
    AppSettings,
    ensure_project_dirs,
    load_settings,
    save_settings,
)
from app.cube.cube_command_builder import write_cubelite_low_vram_template
from app.cube.low_vram_profiles import PROFILES, get_profile
from app.cube.model_manager import validate_cube_install
from app.cube.prompt_presets import PROMPT_GUIDANCE, PROMPT_PRESETS
from app.optimization.texture_generator import DEFAULT_DIFFUSERS_MODEL, QUALITY_DIFFUSERS_MODEL
from app.quality.candidate_search import CandidateSearchConfig, run_candidate_search
from app.reporting.case_study import discover_case_study_assets, generate_case_study_pack, summarize_case_study_assets
from app.system.dependency_checker import check_dependencies
from app.system.gpu_detector import detect_system
from app.ui.components import list_recent_files


def _streamlit():
    import streamlit as st
    return st


def _settings_from_ui(st, current: AppSettings) -> AppSettings:
    cube_repo = st.text_input("Cube 3D repo path", value=current.cube_repo_path)
    weights = st.text_input("Model weights path", value=current.model_weights_path)
    outputs = st.text_input("Outputs folder", value=current.outputs_dir)
    exports = st.text_input("Exports folder", value=current.exports_dir)
    default_profile = st.selectbox(
        "Default profile",
        list(PROFILES.keys()),
        index=list(PROFILES.keys()).index(current.default_profile) if current.default_profile in PROFILES else 0,
    )
    target_faces = st.number_input("Default target triangle count", min_value=1000, max_value=100000, value=current.default_target_face_count, step=1000)
    texture_provider = st.selectbox(
        "Texture provider",
        ["studio", "procedural", "diffusers"],
        index=["studio", "procedural", "diffusers"].index(current.texture_provider) if current.texture_provider in {"studio", "procedural", "diffusers"} else 0,
    )
    model_presets = {
        "Tiny smoke-test model": DEFAULT_DIFFUSERS_MODEL,
        "Stable Diffusion 1.5": QUALITY_DIFFUSERS_MODEL,
        "Custom": current.texture_model_id,
    }
    if current.texture_model_id == DEFAULT_DIFFUSERS_MODEL:
        model_index = 0
    elif current.texture_model_id == QUALITY_DIFFUSERS_MODEL:
        model_index = 1
    else:
        model_index = 2
    selected_model = st.selectbox(
        "Diffusers model preset",
        list(model_presets.keys()),
        index=model_index,
    )
    texture_model = st.text_input("Diffusers texture model", value=model_presets[selected_model])
    texture_steps = st.number_input("Texture inference steps", min_value=1, max_value=80, value=current.texture_steps, step=1)
    texture_size = st.selectbox(
        "Texture atlas size",
        [256, 512, 768, 1024],
        index=[256, 512, 768, 1024].index(current.texture_size) if current.texture_size in {256, 512, 768, 1024} else 3,
    )
    include_paths = st.checkbox("Include full private local paths in reports", value=current.include_private_paths_in_reports)
    return AppSettings(
        cube_repo_path=cube_repo,
        model_weights_path=weights,
        outputs_dir=outputs,
        exports_dir=exports,
        reports_dir=current.reports_dir,
        benchmarks_dir=current.benchmarks_dir,
        default_profile=default_profile,
        default_target_face_count=int(target_faces),
        texture_provider=texture_provider,
        texture_model_id=texture_model,
        texture_steps=int(texture_steps),
        texture_size=int(texture_size),
        include_private_paths_in_reports=include_paths,
    )


def _show_mesh_stats(st, stats: dict[str, object] | None) -> None:
    if not stats:
        st.info("No mesh stats yet.")
        return
    cols = st.columns(4)
    cols[0].metric("Vertices", stats.get("vertex_count", 0))
    cols[1].metric("Triangles", stats.get("triangle_count", 0))
    cols[2].metric("File MB", stats.get("file_size_mb", 0))
    cols[3].metric("Objects", stats.get("object_count") or "n/a")
    if stats.get("warnings"):
        st.warning("\n".join(str(item) for item in stats["warnings"]))
    if stats.get("error_message"):
        st.error(str(stats["error_message"]))


def generate_tab(st, settings: AppSettings) -> None:
    st.caption("Dry run mode uses a sample mesh and does not call Cube 3D.")
    preset = st.selectbox("Preset prompt", ["Custom"] + PROMPT_PRESETS)
    default_prompt = "" if preset == "Custom" else preset
    prompt = st.text_area("Prompt", value=default_prompt or PROMPT_GUIDANCE["good"], height=90)
    profile_name = st.selectbox("Profile", list(PROFILES.keys()), index=list(PROFILES.keys()).index(settings.default_profile) if settings.default_profile in PROFILES else 0)
    col_a, col_b, col_c = st.columns(3)
    dry_run = col_a.toggle("Dry run", value=True)
    simplify = col_b.toggle("Simplify mesh", value=get_profile(profile_name).simplify_after_generation)
    package_export = col_c.toggle("Package export", value=True)
    st.info("Good prompt: " + PROMPT_GUIDANCE["good"])
    with st.expander("Prompt guidance"):
        st.write("Bad prompt: " + PROMPT_GUIDANCE["bad"])
        for note in PROMPT_GUIDANCE["notes"]:
            st.write(f"- {note}")

    if st.button("Generate asset", type="primary"):
        if not prompt.strip():
            st.error("Enter a prompt before generating.")
            return
        with st.status("Running CubeLite pipeline...", expanded=True) as status:
            row, details = run_single_pipeline(
                prompt=prompt,
                profile=get_profile(profile_name),
                cube_repo_path=settings.cube_repo_path,
                model_weights_path=settings.model_weights_path,
                outputs_dir=Path(settings.outputs_dir),
                exports_dir=Path(settings.exports_dir),
                dry_run=dry_run,
                package_export=package_export,
                simplify=simplify,
                texture_provider=settings.texture_provider,
                texture_model_id=settings.texture_model_id,
                texture_steps=settings.texture_steps,
                texture_size=settings.texture_size,
            )
            status.update(label="Pipeline complete", state="complete")
        st.session_state["last_generation_details"] = details
        st.session_state["last_generation_row"] = row.to_dict()

    details = st.session_state.get("last_generation_details")
    row = st.session_state.get("last_generation_row")
    if details and row:
        st.subheader("Latest Result")
        cols = st.columns(4)
        cols[0].metric("Status", "Success" if row["success"] else "Failed")
        cols[1].metric("Seconds", f"{row['generation_time_seconds']:.2f}")
        cols[2].metric("Peak VRAM", row["peak_vram_gb"] if row["peak_vram_gb"] is not None else "n/a")
        cols[3].metric("Readiness", row["readiness_score"] if row["readiness_score"] is not None else "n/a")
        _show_mesh_stats(st, details.get("mesh_stats"))
        readiness = details.get("readiness") or {}
        st.write(f"Roblox readiness: **{readiness.get('status', 'n/a')}**")
        for warning in readiness.get("warnings", []):
            st.warning(warning)
        export = details.get("export") or {}
        render = details.get("render") or {}
        inspection_render = details.get("inspection_render") or {}
        finished_asset = details.get("finished_asset") or {}
        if render.get("success") and render.get("output_path"):
            st.image(render["output_path"], caption="Local mesh preview")
        elif render.get("error_message"):
            st.info(render["error_message"])
        if inspection_render.get("success") and inspection_render.get("output_path"):
            st.image(inspection_render["output_path"], caption="Multi-angle geometry inspection")
        elif inspection_render.get("error_message"):
            st.info(inspection_render["error_message"])
        if finished_asset.get("success"):
            st.success(f"Textured OBJ: {finished_asset.get('textured_obj_path')}")
            if finished_asset.get("texture_path"):
                st.image(finished_asset["texture_path"], caption="Generated texture atlas")
            map_cols = st.columns(3)
            if finished_asset.get("normal_path"):
                map_cols[0].image(finished_asset["normal_path"], caption="Normal map")
            if finished_asset.get("roughness_path"):
                map_cols[1].image(finished_asset["roughness_path"], caption="Roughness map")
            if finished_asset.get("metallic_path"):
                map_cols[2].image(finished_asset["metallic_path"], caption="Metallic map")
            texture_stats = finished_asset.get("texture_stats") or {}
            if texture_stats.get("production_score") is not None:
                st.metric("Texture QA", f"{texture_stats['production_score']}/100")
            for warning in texture_stats.get("warnings") or []:
                st.warning(warning)
        elif finished_asset.get("error_message"):
            st.info(f"Finishing skipped: {finished_asset['error_message']}")
        if export.get("export_dir"):
            st.success(f"Export folder: {export['export_dir']}")
        with st.expander("Logs"):
            st.code((details.get("generation") or {}).get("raw_logs", ""), language="text")


def benchmark_tab(st, settings: AppSettings) -> None:
    prompt_count = st.slider("Max prompts", min_value=1, max_value=len(BENCHMARK_PROMPTS), value=3)
    profiles = st.multiselect("Profiles to test", ["Low VRAM", "6GB Quality", "Balanced", "High Quality", "Benchmark Safe"], default=["Low VRAM", "6GB Quality"])
    dry_run = st.toggle("Dry run benchmark", value=True)
    create_report = st.toggle("Generate technical report", value=True)
    if st.button("Start benchmark", type="primary"):
        progress_rows: list[dict[str, object]] = []
        table = st.empty()

        def on_row(row):
            progress_rows.append(row.to_dict())
            table.dataframe(progress_rows, use_container_width=True)

        result = run_benchmark(
            prompts=BENCHMARK_PROMPTS,
            profile_names=profiles or ["Low VRAM"],
            max_prompts=prompt_count,
            dry_run=dry_run,
            cube_repo_path=settings.cube_repo_path,
            model_weights_path=settings.model_weights_path,
            benchmarks_dir=Path(settings.benchmarks_dir),
            outputs_dir=Path(settings.outputs_dir),
            exports_dir=Path(settings.exports_dir),
            reports_dir=Path(settings.reports_dir),
            create_report=create_report,
            texture_provider=settings.texture_provider,
            texture_model_id=settings.texture_model_id,
            texture_steps=settings.texture_steps,
            texture_size=settings.texture_size,
            on_row=on_row,
        )
        st.session_state["last_benchmark"] = result.__dict__ | {"rows": [row.to_dict() for row in result.rows]}
        st.success(f"Benchmark saved: {result.csv_path}")
        if result.report_path:
            st.success(f"Technical report: {result.report_path}")

    last = st.session_state.get("last_benchmark")
    if last:
        st.subheader("Latest Benchmark")
        st.dataframe(last["rows"], use_container_width=True)
        st.write(f"CSV: {last['csv_path']}")
        st.write(f"JSON: {last['json_path']}")
        if last.get("report_path"):
            st.write(f"Report: {last['report_path']}")


def curation_tab(st, settings: AppSettings) -> None:
    st.caption("Run multiple candidates and reject weak geometry before treating anything as portfolio-worthy.")
    prompt = st.text_area("Prompt to curate", value="low poly wooden crate game prop, clean silhouette", height=80)
    profile_name = st.selectbox("Search profile", ["6GB Quality", "Balanced", "Low VRAM", "Benchmark Safe"], index=0)
    seeds_text = st.text_input("Seeds", value="101 202 303")
    dry_run = st.toggle("Dry run curation", value=True)
    target_faces = st.number_input("Target triangles", min_value=1000, max_value=60000, value=16000, step=1000)
    if st.button("Run candidate curation", type="primary"):
        seeds = tuple(int(seed) for seed in seeds_text.replace(",", " ").split() if seed.strip())
        result = run_candidate_search(
            CandidateSearchConfig(
                prompt=prompt,
                profile_name=profile_name,
                seeds=seeds or (101, 202, 303),
                target_face_count=int(target_faces),
                dry_run=dry_run,
            ),
            cube_repo_path=settings.cube_repo_path,
            model_weights_path=settings.model_weights_path,
            outputs_dir=Path(settings.outputs_dir),
            reports_dir=Path(settings.reports_dir),
        )
        st.session_state["last_curation"] = result.to_dict()
        st.success(f"Curation JSON: {result.json_path}")
        st.success(f"Curation report: {Path(result.json_path).with_suffix('.md')}")

    last = st.session_state.get("last_curation")
    if last:
        best = last.get("best_candidate")
        if best:
            st.subheader("Best Candidate")
            cols = st.columns(4)
            cols[0].metric("Score", best.get("quality_score"))
            cols[1].metric("Geometry", best.get("geometry_status"))
            cols[2].metric("Triangles", best.get("triangle_count") or "n/a")
            cols[3].metric("Seed", best.get("seed"))
            for warning in best.get("reject_reasons") or []:
                st.warning(warning)
            if best.get("render_path"):
                st.image(best["render_path"], caption="Best candidate inspection plate")
            st.write(f"Export: {best.get('export_path') or best.get('output_path')}")
        st.subheader("Candidates")
        st.dataframe(last.get("candidates", []), use_container_width=True)


def results_tab(st) -> None:
    st.subheader("Recent Outputs")
    for path in list_recent_files(OUTPUTS_DIR, ("*.obj",), limit=8):
        st.write(str(path))
    st.subheader("Recent Exports")
    for path in list_recent_files(EXPORTS_DIR, ("metadata.json",), limit=8):
        with st.expander(str(path.parent)):
            preview = path.parent / "preview.png"
            if preview.exists():
                st.image(str(preview), caption=path.parent.name)
            try:
                metadata = json.loads(path.read_text(encoding="utf-8"))
                cols = st.columns(4)
                cols[0].metric("Profile", metadata.get("profile", "n/a"))
                cols[1].metric("Readiness", metadata.get("readiness_score", "n/a"))
                cols[2].metric("Peak VRAM", metadata.get("peak_vram_gb", "n/a"))
                cols[3].metric("Seconds", metadata.get("generation_time_seconds", "n/a"))
                st.json(metadata)
            except Exception:
                st.write(str(path))
    st.subheader("Recent Benchmark Reports")
    for path in list_recent_files(REPORTS_DIR, ("*.md",), limit=8):
        st.write(str(path))
    st.subheader("Recent Benchmark Data")
    for path in list_recent_files(BENCHMARKS_DIR, ("*.csv", "*.json"), limit=8):
        st.write(str(path))


def case_study_tab(st, settings: AppSettings) -> None:
    assets = discover_case_study_assets()
    summary = summarize_case_study_assets(assets)
    st.caption("Portfolio-ready evidence generated from local real Cube 3D outputs.")
    cols = st.columns(5)
    cols[0].metric("Real assets", summary.asset_count)
    cols[1].metric("With stats", summary.successful_asset_count)
    cols[2].metric("Peak VRAM", f"{summary.max_peak_vram_gb:.2f} GB" if summary.max_peak_vram_gb is not None else "n/a")
    cols[3].metric("Avg seconds", f"{summary.average_generation_seconds:.1f}" if summary.average_generation_seconds is not None else "n/a")
    cols[4].metric("Avg readiness", f"{summary.average_readiness_score:.1f}/100" if summary.average_readiness_score is not None else "n/a")

    st.markdown(
        "**Case-study thesis:** CubeLite Studio turns Cube 3D from a high-VRAM research/demo setup into a measurable local creator workflow with real VRAM telemetry, mesh statistics, Roblox-readiness notes, and export packages."
    )
    st.info("Honest framing: this is independent, not official Roblox validation, and it does not redistribute Cube 3D model weights.")

    if st.button("Generate Roblox-reviewable case study pack", type="primary"):
        markdown_path, contact_sheet_path, html_path = generate_case_study_pack(Path(settings.reports_dir))
        st.success(f"Markdown case study: {markdown_path}")
        st.success(f"HTML case study: {html_path}")
        if contact_sheet_path:
            st.image(str(contact_sheet_path), caption="Real CubeLite output contact sheet")

    for asset in assets:
        with st.expander(asset.prompt or asset.name):
            if asset.preview_path:
                st.image(asset.preview_path, caption=asset.name)
            asset_cols = st.columns(4)
            asset_cols[0].metric("Profile", asset.profile)
            asset_cols[1].metric("Triangles", asset.triangle_count if asset.triangle_count is not None else "n/a")
            asset_cols[2].metric("Peak VRAM", f"{asset.peak_vram_gb:.2f} GB" if asset.peak_vram_gb is not None else "n/a")
            asset_cols[3].metric("Readiness", asset.readiness_score if asset.readiness_score is not None else "n/a")
            st.write(f"Quality: **{asset.quality_label}**")
            if asset.reviewer_note:
                st.write(asset.reviewer_note)
            st.write(f"OBJ: {asset.original_obj_path or 'n/a'}")


def system_tab(st) -> None:
    diagnostics = detect_system()
    cols = st.columns(4)
    cols[0].metric("GPU", diagnostics.gpu_name)
    cols[1].metric("Total VRAM", diagnostics.total_vram_gb if diagnostics.total_vram_gb is not None else "n/a")
    cols[2].metric("Free VRAM", diagnostics.free_vram_gb if diagnostics.free_vram_gb is not None else "n/a")
    cols[3].metric("Recommended", diagnostics.recommended_profile)
    st.write(
        {
            "OS": diagnostics.os,
            "CPU": diagnostics.cpu,
            "RAM GB": diagnostics.ram_gb,
            "Python": diagnostics.python_version,
            "PyTorch": diagnostics.pytorch_version,
            "CUDA available": diagnostics.cuda_available,
            "CUDA version": diagnostics.cuda_version,
            "Apple Silicon MPS": diagnostics.mps_available,
        }
    )
    for warning in diagnostics.warnings:
        st.warning(warning)
    st.subheader("Dependency Check")
    st.dataframe([dep.__dict__ for dep in check_dependencies()], use_container_width=True)


def settings_tab(st, settings: AppSettings) -> AppSettings:
    updated = _settings_from_ui(st, settings)
    if st.button("Save settings"):
        save_settings(updated)
        st.success("Settings saved.")
    status = validate_cube_install(updated.cube_repo_path, updated.model_weights_path)
    st.subheader("Cube 3D Configuration")
    st.write(f"Repo found: {status.repo_exists}")
    st.write(f"Weights found: {status.weights_exist}")
    st.write(f"Command template found: {status.command_template_exists}")
    for message in status.messages:
        st.info(message)
    if status.repo_exists:
        overwrite = st.checkbox("Overwrite existing CubeLite command template", value=False)
        if st.button("Write CubeLite low-VRAM command template"):
            try:
                template_path = write_cubelite_low_vram_template(
                    updated.cube_repo_path,
                    overwrite=overwrite,
                )
                st.success(f"Command template written: {template_path}")
            except Exception as exc:
                st.error(str(exc))
    with st.expander("Real generation command template"):
        st.markdown(
            """CubeLite can write `cubelite_cube_command.json` into your local Cube 3D repo. The generated template calls CubeLite's staged low-VRAM runner:

```json
{
  "command": ["<cube-python>", "<cubelite>/app/cube/cubelite_low_vram_generate.py", "--prompt", "{prompt}", "--output-dir", "{output_dir}"]
}
```

Only placeholders included in the template are passed to Cube 3D. Profile settings that are not supported by the detected Cube install remain CubeLite workflow notes or post-processing settings.
"""
        )
    return updated


def about_tab(st) -> None:
    st.markdown(
        """CubeLite Studio is an independent tool that wraps and benchmarks Roblox Cube 3D. It is not affiliated with, endorsed by, or sponsored by Roblox Corporation.

This tool does not include or redistribute Cube 3D model weights. Users must obtain model files from official sources and follow the original license.

CubeLite Studio focuses on an experimental low-VRAM workflow, benchmark data, mesh analysis, optional simplification, and Roblox-friendly export packaging for local creator workflows.
"""
    )


def run_streamlit_app() -> None:
    ensure_project_dirs()
    st = _streamlit()
    st.set_page_config(page_title="CubeLite Studio", page_icon="CL", layout="wide")
    st.title("CubeLite Studio")
    st.subheader("Low-VRAM Cube 3D workflow for Roblox creators")
    st.caption(
        "CubeLite Studio is an independent local toolkit that helps Roblox creators test Cube 3D on consumer GPUs, measure VRAM usage, optimize generated meshes, and export Roblox-friendly asset packages."
    )

    settings = load_settings()
    tabs = st.tabs(["Generate", "Benchmark", "Curation", "Results", "System Check", "Settings", "Case Study", "About"])
    with tabs[0]:
        generate_tab(st, settings)
    with tabs[1]:
        benchmark_tab(st, settings)
    with tabs[2]:
        curation_tab(st, settings)
    with tabs[3]:
        results_tab(st)
    with tabs[4]:
        system_tab(st)
    with tabs[5]:
        settings_tab(st, settings)
    with tabs[6]:
        case_study_tab(st, settings)
    with tabs[7]:
        about_tab(st)


if __name__ == "__main__":
    run_streamlit_app()
