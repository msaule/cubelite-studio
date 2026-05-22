from __future__ import annotations

from app.config import ensure_project_dirs
from app.ui.streamlit_app import run_streamlit_app


def main() -> None:
    ensure_project_dirs()
    run_streamlit_app()


if __name__ == "__main__":
    main()
