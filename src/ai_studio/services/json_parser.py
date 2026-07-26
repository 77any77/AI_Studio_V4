from __future__ import annotations

import json
from typing import Any


class StructuredOutputError(ValueError):
    pass


def extract_json(text: str) -> Any:
    """从模型回复中提取 JSON，兼容 Markdown 代码块和前后解释文字。"""
    cleaned = text.strip()

    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    candidates: list[str] = []

    first_object = cleaned.find("{")
    last_object = cleaned.rfind("}")
    if first_object >= 0 and last_object > first_object:
        candidates.append(cleaned[first_object:last_object + 1])

    first_array = cleaned.find("[")
    last_array = cleaned.rfind("]")
    if first_array >= 0 and last_array > first_array:
        candidates.append(cleaned[first_array:last_array + 1])

    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue

    raise StructuredOutputError(
        "模型没有返回有效 JSON。请在“原始结果”页查看模型回复。"
    )
