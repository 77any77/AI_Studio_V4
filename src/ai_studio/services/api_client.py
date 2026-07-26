from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

from ai_studio.models.config import APIProfile


class APIClientError(RuntimeError):
    pass


@dataclass(slots=True)
class ConnectionResult:
    text: str
    elapsed_seconds: float
    model: str
    profile_name: str


class OpenAICompatibleClient:
    def __init__(self, profile: APIProfile):
        self.profile = profile

    def endpoint(self) -> str:
        base = self.profile.base_url.strip().rstrip("/")
        if not base:
            raise APIClientError("Base URL 不能为空。")
        if base.endswith("/chat/completions"):
            return base
        return f"{base}/chat/completions"

    def chat(
        self,
        system: str,
        user: str,
        temperature: float = 0.2,
    ) -> str:
        if not self.profile.enabled:
            raise APIClientError(f"接口“{self.profile.name}”已被停用。")
        if not self.profile.model.strip():
            raise APIClientError("模型名称不能为空。")

        payload = {
            "model": self.profile.model.strip(),
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
        }

        headers = {"Content-Type": "application/json"}
        if self.profile.api_key.strip():
            headers["Authorization"] = (
                f"Bearer {self.profile.api_key.strip()}"
            )

        request = urllib.request.Request(
            self.endpoint(),
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=self.profile.timeout_seconds,
            ) as response:
                raw = response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise APIClientError(
                f"HTTP {exc.code}：{detail[:1200]}"
            ) from exc
        except urllib.error.URLError as exc:
            raise APIClientError(
                f"网络连接失败：{exc.reason}"
            ) from exc
        except TimeoutError as exc:
            raise APIClientError(
                f"请求超时（{self.profile.timeout_seconds} 秒）。"
            ) from exc

        try:
            data = json.loads(raw)
            return data["choices"][0]["message"]["content"]
        except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
            raise APIClientError(
                f"接口返回格式无法识别：{raw[:1200]}"
            ) from exc

    def test_connection(self) -> ConnectionResult:
        start = time.perf_counter()
        text = self.chat(
            "你是连接测试助手。",
            "只回复：连接成功",
            temperature=0,
        )
        elapsed = time.perf_counter() - start
        return ConnectionResult(
            text=text,
            elapsed_seconds=elapsed,
            model=self.profile.model,
            profile_name=self.profile.name,
        )
