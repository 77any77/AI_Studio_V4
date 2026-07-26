from __future__ import annotations

import os
from pathlib import Path


def user_data_dir() -> Path:
    base = os.getenv("APPDATA")
    if base:
        path = Path(base) / "AI_Studio_V4"
    else:
        path = Path.home() / ".ai_studio_v4"
    path.mkdir(parents=True, exist_ok=True)
    return path


def config_path() -> Path:
    return user_data_dir() / "config.json"


def projects_dir() -> Path:
    path = user_data_dir() / "projects"
    path.mkdir(parents=True, exist_ok=True)
    return path


def logs_dir() -> Path:
    path = user_data_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path
