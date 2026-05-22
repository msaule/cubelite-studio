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
from app.cube.low_vram_profiles import PROFILES, get_profile
from app.cube.model_manager import validate_cube_install
from app.cube.prompt_presets import PROMPT_GUIDANCE, PROMPT_PRESETS
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
        if render.get("success") and render.get("output_path"):
            st.image(render["output_path"], caption="Local mesh preview")
        elif render.get("error_message"):
            st.info(render["error_message"])
        if export.get("export_dir"):
            st.success(f"Export folder: {export['export_dir']}")
        with st.expander("Logs"):
            st.code((details.get("generation") or {}).get("raw_logs", ""), language="text")


def benchmark_tab(st, settings: AppSettings) -> None:
    prompt_count = st.slider("Max prompts", min_value=1, max_value=len(BENCHMARK_PROMPTS), value=3)
    profiles = st.multiselect("Profiles to test", ["Low VRAM", "Balanced", "High Quality", "Benchmark Safe"], default=["Low VRAM", "Balanced"])
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


def results_tab(st) -> None:
    st.subheader("Recent Outputs")
    for path in list_recent_files(OUTPUTS_DIR, ("*.obj",), limit=8):
        st.write(str(path))
    st.subheader("Recent Exports")
    for path in list_recent_files(EXPORTS_DIR, ("metadata.json",), limit=8):
        with st.expander(str(path.parent)):
            try:
                st.json(json.loads(path.read_text(encoding="utf-8")))
            except Exception:
                st.write(str(path))
    st.subheader("Recent Benchmark Reports")
    for path in list_recent_files(REPORTS_DIR, ("*.md",), limit=8):
        st.write(str(path))
    st.subheader("Recent Benchmark Data")
    for path in list_recent_files(BENCHMARKS_DIR, ("*.csv", "*.json"), limit=8):
        st.write(str(path))


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
    with st.expander("Real generation command template"):
        st.markdown(
            """Create `cubelite_cube_command.json` in your local Cube 3D repo when you are ready to connect a specific Cube release:

```json
{
  "command": ["{python}", "generate.py", "--prompt", "{prompt}", "--weights", "{weights_path}", "--output_dir", "{output_dir}"]
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
    tabs = st.tabs(["Generate", "Benchmark", "Results", "System Check", "Settings", "About"])
    with tabs[0]:
        generate_tab(st, settings)
    with tabs[1]:
        benchmark_tab(st, settings)
    with tabs[2]:
        results_tab(st)
    with tabs[3]:
        system_tab(st)
    with tabs[4]:
        settings_tab(st, settings)
    with tabs[5]:
        about_tab(st)


if __name__ == "__main__":
    run_streamlit_app()
