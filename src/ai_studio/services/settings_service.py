from __future__ import annotations

from ai_studio.core.paths import config_path
from ai_studio.core.storage import read_json, write_json
from ai_studio.models.config import APISettings


class SettingsService:
    def load(self) -> APISettings:
        return APISettings.from_dict(read_json(config_path(), {}))

    def save(self, settings: APISettings) -> None:
        write_json(config_path(), settings.to_dict())
