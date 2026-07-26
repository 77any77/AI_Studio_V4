from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from ai_studio.services.json_parser import extract_json
from ai_studio.services.router_service import APIRouterService


STORY_ANALYSIS_SYSTEM = """你是工业级AI漫剧故事分析引擎。
必须忠于小说原文，不改变人物关系、剧情走向和关键设定。
只输出严格JSON，不要输出Markdown代码块，不要添加解释。
"""

STORY_ANALYSIS_USER = """请分析以下小说，输出JSON：
{
  "title": "作品名或暂定名",
  "genre": "题材",
  "era": "时代背景",
  "world": "世界观和社会环境",
  "logline": "一句话故事核心",
  "main_conflict": "核心冲突",
  "main_plot": "主线",
  "subplots": ["支线"],
  "tone": "整体情绪和风格",
  "audience_hooks": ["吸引观众的钩子"],
  "story_beats": [
    {
      "index": 1,
      "event": "关键事件",
      "emotion": "情绪",
      "conflict": "冲突",
      "turning_point": "转折"
    }
  ]
}

小说原文：
"""

CHARACTER_SYSTEM = """你是AI漫剧人物资产设计师。
必须依据小说原文提取人物，不杜撰不存在的重要角色。
同一人物的稳定外貌、身份、关系和性格必须保持一致。
只输出严格JSON，不要输出Markdown代码块。
"""

CHARACTER_USER = """依据小说原文和故事分析提取人物，输出JSON：
{
  "characters": [
    {
      "character_id": "C001",
      "name": "姓名",
      "role": "主角/配角/反派/群众",
      "gender": "性别或未知",
      "age": "明确年龄或年龄段",
      "identity": "身份职业",
      "appearance": {
        "face": "脸型五官",
        "hair": "发型发色",
        "body": "身形身高",
        "distinctive_features": "稳定识别特征"
      },
      "default_costume": "基础服装",
      "personality": ["性格"],
      "relationships": [
        {"target": "人物", "relation": "关系"}
      ],
      "motivation": "核心动机",
      "voice": "建议声线",
      "visual_prompt": "全身人物设定图提示词"
    }
  ]
}

小说原文：
"""

SCENE_SYSTEM = """你是AI漫剧场景资产设计师。
必须依据小说原文提取可复用场景，不将同一地点的细微变化重复成多个场景。
只输出严格JSON，不要输出Markdown代码块。
"""

SCENE_USER = """依据小说原文和故事分析提取场景，输出JSON：
{
  "scenes": [
    {
      "scene_id": "L001",
      "name": "场景名称",
      "location_type": "室内/室外",
      "era": "时代",
      "time_options": ["白天", "夜晚"],
      "environment": "空间结构和环境",
      "key_visuals": ["稳定视觉元素"],
      "lighting": "基础光影",
      "atmosphere": "氛围",
      "visual_prompt": "场景资产图提示词"
    }
  ]
}

小说原文：
"""

PROP_SYSTEM = """你是AI漫剧道具资产设计师。
只提取影响剧情、人物身份或镜头连续性的关键道具。
只输出严格JSON，不要输出Markdown代码块。
"""

PROP_USER = """依据小说原文和故事分析提取关键道具，输出JSON：
{
  "props": [
    {
      "prop_id": "P001",
      "name": "道具名称",
      "owner": "归属人物或场景",
      "appearance": "外观材质",
      "story_function": "剧情用途",
      "continuity": "连续性注意事项",
      "visual_prompt": "道具资产图提示词"
    }
  ]
}

小说原文：
"""


@dataclass(slots=True)
class PipelineResult:
    analysis: dict[str, Any]
    characters: list[dict[str, Any]]
    scenes: list[dict[str, Any]]
    props: list[dict[str, Any]]
    raw_results: dict[str, str]


class NovelPipeline:
    def __init__(self, router: APIRouterService):
        self.router = router

    def run_story_analysis(self, novel: str) -> tuple[dict[str, Any], str]:
        raw = self.router.chat(
            "story_analysis",
            STORY_ANALYSIS_SYSTEM,
            STORY_ANALYSIS_USER + novel,
            temperature=0.25,
        )
        parsed = extract_json(raw)
        if not isinstance(parsed, dict):
            raise ValueError("故事分析结果必须是 JSON 对象。")
        return parsed, raw

    def run_character_extract(
        self,
        novel: str,
        analysis: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], str]:
        prompt = (
            CHARACTER_USER
            + novel
            + "\n\n故事分析：\n"
            + json.dumps(analysis, ensure_ascii=False)
        )
        raw = self.router.chat(
            "character_extract",
            CHARACTER_SYSTEM,
            prompt,
            temperature=0.2,
        )
        parsed = extract_json(raw)
        if not isinstance(parsed, dict):
            raise ValueError("人物提取结果必须是 JSON 对象。")
        characters = parsed.get("characters", [])
        if not isinstance(characters, list):
            raise ValueError("characters 字段必须是数组。")
        return characters, raw

    def run_scene_extract(
        self,
        novel: str,
        analysis: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], str]:
        prompt = (
            SCENE_USER
            + novel
            + "\n\n故事分析：\n"
            + json.dumps(analysis, ensure_ascii=False)
        )
        raw = self.router.chat(
            "scene_extract",
            SCENE_SYSTEM,
            prompt,
            temperature=0.2,
        )
        parsed = extract_json(raw)
        if not isinstance(parsed, dict):
            raise ValueError("场景提取结果必须是 JSON 对象。")
        scenes = parsed.get("scenes", [])
        if not isinstance(scenes, list):
            raise ValueError("scenes 字段必须是数组。")
        return scenes, raw

    def run_prop_extract(
        self,
        novel: str,
        analysis: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], str]:
        prompt = (
            PROP_USER
            + novel
            + "\n\n故事分析：\n"
            + json.dumps(analysis, ensure_ascii=False)
        )
        raw = self.router.chat(
            "prop_extract",
            PROP_SYSTEM,
            prompt,
            temperature=0.15,
        )
        parsed = extract_json(raw)
        if not isinstance(parsed, dict):
            raise ValueError("道具提取结果必须是 JSON 对象。")
        props = parsed.get("props", [])
        if not isinstance(props, list):
            raise ValueError("props 字段必须是数组。")
        return props, raw

    def run_all(self, novel: str) -> PipelineResult:
        analysis, analysis_raw = self.run_story_analysis(novel)
        characters, characters_raw = self.run_character_extract(
            novel, analysis
        )
        scenes, scenes_raw = self.run_scene_extract(novel, analysis)
        props, props_raw = self.run_prop_extract(novel, analysis)

        return PipelineResult(
            analysis=analysis,
            characters=characters,
            scenes=scenes,
            props=props,
            raw_results={
                "story_analysis": analysis_raw,
                "character_extract": characters_raw,
                "scene_extract": scenes_raw,
                "prop_extract": props_raw,
            },
        )
