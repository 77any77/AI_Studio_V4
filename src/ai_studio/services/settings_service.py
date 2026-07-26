from __future__ import annotations

from ai_studio.core.paths import config_path
from ai_studio.core.storage import read_json, write_json
from ai_studio.models.config import AppSettings


class SettingsService:
    def load(self) -> AppSettings:
        return AppSettings.from_dict(read_json(config_path(), {}))

    def save(self, settings: AppSettings) -> None:
        write_json(config_path(), settings.to_dict())
