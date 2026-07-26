from __future__ import annotations

import json
import urllib.error
import urllib.request

from ai_studio.models.config import APISettings


class APIClientError(RuntimeError):
    pass


class OpenAICompatibleClient:
    def __init__(self, settings: APISettings):
        self.settings = settings

    def endpoint(self) -> str:
        base = self.settings.base_url.strip().rstrip("/")
        if not base:
            raise APIClientError("Base URL 不能为空")
        if base.endswith("/chat/completions"):
            return base
        return f"{base}/chat/completions"

    def chat(self, system: str, user: str, temperature: float = 0.2) -> str:
        if not self.settings.model.strip():
            raise APIClientError("模型名称不能为空")

        body = {
            "model": self.settings.model.strip(),
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
        }
        headers = {"Content-Type": "application/json"}
        if self.settings.api_key.strip():
            headers["Authorization"] = f"Bearer {self.settings.api_key.strip()}"

        req = urllib.request.Request(
            self.endpoint(),
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(
                req, timeout=self.settings.timeout_seconds
            ) as response:
                raw = response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise APIClientError(f"HTTP {exc.code}: {detail[:1000]}") from exc
        except urllib.error.URLError as exc:
            raise APIClientError(f"网络连接失败: {exc.reason}") from exc

        try:
            payload = json.loads(raw)
            return payload["choices"][0]["message"]["content"]
        except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
            raise APIClientError(f"无法解析接口返回: {raw[:1000]}") from exc

    def test_connection(self) -> str:
        return self.chat("你是连接测试助手。", "只回复：连接成功", 0)
