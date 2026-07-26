from __future__ import annotations

from dataclasses import asdict, dataclass, field
from uuid import uuid4


PROVIDER_PRESETS: dict[str, dict[str, str]] = {
    "OpenAI": {
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4.1-mini",
    },
    "DeepSeek": {
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
    },
    "通义兼容": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen-plus",
    },
    "Ollama": {
        "base_url": "http://127.0.0.1:11434/v1",
        "model": "qwen2.5:14b",
    },
    "LM Studio": {
        "base_url": "http://127.0.0.1:1234/v1",
        "model": "local-model",
    },
    "自定义": {
        "base_url": "",
        "model": "",
    },
}


TASK_LABELS: dict[str, str] = {
    "rewrite": "小说改写",
    "story_analysis": "故事分析",
    "character_extract": "人物提取",
    "scene_extract": "场景提取",
    "prop_extract": "道具提取",
    "storyboard": "导演分镜",
    "prompt_compile": "视频 Prompt 编译",
    "quality_review": "质量复核",
}


@dataclass(slots=True)
class APIProfile:
    profile_id: str = field(default_factory=lambda: uuid4().hex)
    name: str = "默认接口"
    provider: str = "OpenAI"
    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    model: str = "gpt-4.1-mini"
    timeout_seconds: int = 120
    enabled: bool = True

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict | None) -> "APIProfile":
        value = value or {}
        defaults = cls()
        return cls(
            profile_id=str(value.get("profile_id") or defaults.profile_id),
            name=str(value.get("name") or defaults.name),
            provider=str(value.get("provider") or defaults.provider),
            base_url=str(value.get("base_url") or defaults.base_url),
            api_key=str(value.get("api_key") or ""),
            model=str(value.get("model") or defaults.model),
            timeout_seconds=int(
                value.get("timeout_seconds", defaults.timeout_seconds)
            ),
            enabled=bool(value.get("enabled", True)),
        )


@dataclass(slots=True)
class AppSettings:
    profiles: list[APIProfile] = field(default_factory=list)
    task_routes: dict[str, str] = field(default_factory=dict)

    @classmethod
    def default(cls) -> "AppSettings":
        profile = APIProfile()
        return cls(
            profiles=[profile],
            task_routes={task: profile.profile_id for task in TASK_LABELS},
        )

    def to_dict(self) -> dict:
        return {
            "profiles": [profile.to_dict() for profile in self.profiles],
            "task_routes": dict(self.task_routes),
        }

    @classmethod
    def from_dict(cls, value: dict | None) -> "AppSettings":
        value = value or {}

        # 兼容旧版单接口配置
        if "profiles" not in value and any(
            key in value for key in ("provider", "base_url", "model", "api_key")
        ):
            profile = APIProfile(
                name="旧版默认接口",
                provider=str(value.get("provider") or "OpenAI"),
                base_url=str(
                    value.get("base_url") or "https://api.openai.com/v1"
                ),
                api_key=str(value.get("api_key") or ""),
                model=str(value.get("model") or "gpt-4.1-mini"),
                timeout_seconds=int(value.get("timeout_seconds", 120)),
            )
            return cls(
                profiles=[profile],
                task_routes={task: profile.profile_id for task in TASK_LABELS},
            )

        profiles = [
            APIProfile.from_dict(item)
            for item in value.get("profiles", [])
            if isinstance(item, dict)
        ]
        if not profiles:
            return cls.default()

        valid_ids = {profile.profile_id for profile in profiles}
        first_id = profiles[0].profile_id
        raw_routes = value.get("task_routes", {})
        routes = {}
        for task in TASK_LABELS:
            candidate = str(raw_routes.get(task) or "")
            routes[task] = candidate if candidate in valid_ids else first_id

        return cls(profiles=profiles, task_routes=routes)

    def profile_by_id(self, profile_id: str) -> APIProfile | None:
        return next(
            (profile for profile in self.profiles if profile.profile_id == profile_id),
            None,
        )

    def profile_for_task(self, task_key: str) -> APIProfile:
        profile_id = self.task_routes.get(task_key, "")
        profile = self.profile_by_id(profile_id)
        if profile is not None:
            return profile
        if not self.profiles:
            fallback = APIProfile()
            self.profiles.append(fallback)
            return fallback
        return self.profiles[0]
