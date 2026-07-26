from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True)
class APISettings:
    provider: str = "OpenAI兼容"
    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    model: str = "gpt-4.1-mini"
    timeout_seconds: int = 120

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict | None) -> "APISettings":
        value = value or {}
        return cls(
            provider=str(value.get("provider", cls.provider)),
            base_url=str(value.get("base_url", cls.base_url)),
            api_key=str(value.get("api_key", "")),
            model=str(value.get("model", cls.model)),
            timeout_seconds=int(value.get("timeout_seconds", 120)),
        )
