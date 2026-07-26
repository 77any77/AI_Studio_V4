from __future__ import annotations

from ai_studio.models.config import AppSettings, APIProfile
from ai_studio.services.api_client import OpenAICompatibleClient


class APIRouterService:
    """根据任务类型选择对应 API。"""

    def __init__(self, settings: AppSettings):
        self.settings = settings

    def profile_for(self, task_key: str) -> APIProfile:
        return self.settings.profile_for_task(task_key)

    def client_for(self, task_key: str) -> OpenAICompatibleClient:
        return OpenAICompatibleClient(self.profile_for(task_key))

    def chat(
        self,
        task_key: str,
        system: str,
        user: str,
        temperature: float = 0.2,
    ) -> str:
        return self.client_for(task_key).chat(
            system=system,
            user=user,
            temperature=temperature,
        )
