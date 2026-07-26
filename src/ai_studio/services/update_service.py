from __future__ import annotations

import json
import os
import re
import tempfile
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass(slots=True)
class UpdateInfo:
    current_version: str
    latest_version: str
    release_name: str
    notes: str
    download_url: str
    asset_name: str
    published_at: str
    mandatory: bool = False

    @property
    def has_update(self) -> bool:
        return compare_versions(self.latest_version, self.current_version) > 0


def normalize_version(value: str) -> tuple[int, ...]:
    numbers = re.findall(r"\d+", (value or "").lower().removeprefix("v"))
    return tuple(int(item) for item in numbers[:4]) or (0,)


def compare_versions(left: str, right: str) -> int:
    left_parts = list(normalize_version(left))
    right_parts = list(normalize_version(right))
    width = max(len(left_parts), len(right_parts))
    left_parts += [0] * (width - len(left_parts))
    right_parts += [0] * (width - len(right_parts))
    return (left_parts > right_parts) - (left_parts < right_parts)


class UpdateService:
    def __init__(
        self,
        current_version: str,
        release_api_url: str,
        asset_pattern: str = r"AI-Studio-V4-Update.*\.zip$",
        timeout_seconds: int = 30,
    ) -> None:
        self.current_version = current_version
        self.release_api_url = release_api_url.strip()
        self.asset_pattern = asset_pattern
        self.timeout_seconds = timeout_seconds

    def check_update(self) -> UpdateInfo:
        if not self.release_api_url:
            raise ValueError("尚未配置 GitHub Release API 地址。")

        request = urllib.request.Request(
            self.release_api_url,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "AI-Studio-V4-Updater",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise RuntimeError("没有找到发布版本，请先创建 GitHub Release。") from exc
            if exc.code == 403:
                raise RuntimeError("GitHub 请求受限，私有仓库需要授权。") from exc
            raise RuntimeError(f"检查更新失败：HTTP {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"无法连接更新服务器：{exc.reason}") from exc

        tag = str(payload.get("tag_name") or "")
        latest_version = tag.removeprefix("v")
        if not latest_version:
            raise RuntimeError("Release 数据中缺少版本号。")

        pattern = re.compile(self.asset_pattern, re.IGNORECASE)
        matched: dict[str, Any] | None = None
        assets = payload.get("assets") or []
        for asset in assets:
            if pattern.search(str(asset.get("name") or "")):
                matched = asset
                break
        if matched is None:
            names = "、".join(str(x.get("name") or "") for x in assets) or "无"
            raise RuntimeError(f"没有找到更新压缩包。现有文件：{names}")

        body = str(payload.get("body") or "").strip()
        return UpdateInfo(
            current_version=self.current_version,
            latest_version=latest_version,
            release_name=str(payload.get("name") or tag),
            notes=body or "本次更新暂无说明。",
            download_url=str(matched.get("browser_download_url") or ""),
            asset_name=str(matched.get("name") or "update.zip"),
            published_at=str(payload.get("published_at") or ""),
            mandatory="[mandatory]" in body.lower(),
        )

    def download_update(
        self,
        update: UpdateInfo,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> Path:
        update_dir = Path(tempfile.gettempdir()) / "AI_Studio_V4_Update"
        update_dir.mkdir(parents=True, exist_ok=True)
        destination = update_dir / update.asset_name
        request = urllib.request.Request(
            update.download_url,
            headers={"User-Agent": "AI-Studio-V4-Updater"},
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response, destination.open("wb") as target:
                total = int(response.headers.get("Content-Length", 0) or 0)
                done = 0
                while True:
                    block = response.read(1024 * 256)
                    if not block:
                        break
                    target.write(block)
                    done += len(block)
                    if progress_callback:
                        progress_callback(done, total)
        except Exception:
            destination.unlink(missing_ok=True)
            raise

        if not zipfile.is_zipfile(destination):
            destination.unlink(missing_ok=True)
            raise RuntimeError("下载的更新包不是有效 ZIP 文件。")
        with zipfile.ZipFile(destination) as archive:
            bad = archive.testzip()
            if bad:
                raise RuntimeError(f"更新包损坏：{bad}")
        return destination


def default_install_dir() -> Path:
    return Path(os.path.abspath(os.sys.executable)).parent


def find_updater_executable(install_dir: Path) -> Path:
    for name in ("AI Studio Updater.exe", "AI_Studio_Updater.exe"):
        candidate = install_dir / name
        if candidate.exists():
            return candidate
    raise FileNotFoundError("没有找到 AI Studio Updater.exe。")
