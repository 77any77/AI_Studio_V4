from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from ai_studio.services.json_parser import extract_json
from ai_studio.services.router_service import APIRouterService


DIRECTOR_SYSTEM = """你是工业级高维视听流总导演。
你的任务是把小说、故事分析和资产信息转化为可拍摄、可生成、可连续衔接的导演分镜。

必须遵守：
1. 不删除、篡改或总结掉关键剧情。
2. 不改变人物关系、台词归属和事件因果。
3. 每个镜头必须写清人物位置、视线、动作和空间关系。
4. 镜头之间必须保持服装、道具、时间、天气、人物状态连续。
5. 单镜头建议5至15秒；复杂台词可拆镜，但不得改台词含义。
6. 输出严格JSON，不要输出Markdown代码块或解释。
"""

DIRECTOR_USER = """请依据小说、故事分析、人物资产、场景资产和道具资产生成导演分镜。

输出JSON：
{
  "episode_title": "本段标题",
  "total_duration": 0,
  "shots": [
    {
      "shot_id": "S001",
      "duration": 8,
      "source_text": "对应小说原文或事件",
      "scene_id": "L001",
      "scene_name": "场景名称",
      "time": "时间",
      "weather": "天气",
      "characters": ["人物"],
      "character_states": [
        {
          "name": "人物名",
          "costume": "当前服装",
          "position": "画面和空间位置",
          "posture": "姿态",
          "gaze": "视线方向",
          "emotion": "情绪",
          "continuity_state": "承接上一镜的状态"
        }
      ],
      "shot_size": "景别",
      "camera_angle": "机位角度",
      "camera_movement": "运镜",
      "composition": "构图",
      "focus": "焦点和景深",
      "lighting": "光影",
      "color": "色彩",
      "action_timeline": [
        {"time": "0-2秒", "action": "动作"},
        {"time": "2-5秒", "action": "动作"}
      ],
      "micro_expression": "表情和微动作",
      "dialogue": [
        {"speaker": "人物", "text": "原台词", "delivery": "语气"}
      ],
      "sound": {
        "environment": "环境音",
        "sfx": ["音效"],
        "bgm": "配乐建议"
      },
      "continuity": {
        "from_previous": "承接上一镜",
        "to_next": "给下一镜的状态",
        "locked_elements": ["必须保持一致的元素"]
      },
      "director_note": "导演意图"
    }
  ]
}

要求：
- shot_id连续编号。
- total_duration等于所有镜头duration之和。
- 关键情绪变化、地点变化、人物进出场应换镜。
- 台词必须属于正确人物。
- 无台词时dialogue为空数组。
- 每镜必须有action_timeline。
"""


PROMPT_SYSTEM = """你是Seedance视频提示词编译器。
将导演分镜编译成适合AI视频生成的中文提示词。
必须忠于分镜，不添加改变剧情的新事件。
每条提示词都要具备人物一致性、空间连续性和秒级动作。
只输出严格JSON，不要输出Markdown代码块。
"""

PROMPT_USER = """将以下导演分镜编译成视频提示词。

输出JSON：
{
  "prompts": [
    {
      "shot_id": "S001",
      "duration": 8,
      "prompt": "完整中文视频提示词",
      "negative_prompt": "需要避免的问题",
      "continuity_reference": "承接信息"
    }
  ]
}

每条prompt必须按以下顺序写：
1. 人物身份和稳定外貌、服装；
2. 场景、时间、天气和空间关系；
3. 景别、机位、构图、焦点；
4. 运镜；
5. 从0秒到结束的动作时间轴；
6. 表情、视线和微动作；
7. 光影、色彩和电影质感；
8. 台词口型与说话人物；
9. 环境音、音效、配乐；
10. 与上一镜和下一镜的连续性。

negative_prompt至少包含：
人物变脸、服装改变、手指异常、肢体畸形、空间跳变、道具消失、
多人身份混乱、口型错位、画面抖动、无意义镜头切换。
"""


@dataclass(slots=True)
class StoryboardResult:
    episode_title: str
    total_duration: int
    shots: list[dict[str, Any]]
    raw: str


@dataclass(slots=True)
class PromptCompileResult:
    prompts: list[dict[str, Any]]
    raw: str


class DirectorEngine:
    def __init__(self, router: APIRouterService):
        self.router = router

    def create_storyboard(
        self,
        novel: str,
        analysis: dict[str, Any],
        characters: list[dict[str, Any]],
        scenes: list[dict[str, Any]],
        props: list[dict[str, Any]],
    ) -> StoryboardResult:
        context = {
            "novel": novel,
            "analysis": analysis,
            "characters": characters,
            "scenes": scenes,
            "props": props,
        }

        raw = self.router.chat(
            "storyboard",
            DIRECTOR_SYSTEM,
            DIRECTOR_USER
            + "\n\n生产资料：\n"
            + json.dumps(context, ensure_ascii=False),
            temperature=0.35,
        )

        parsed = extract_json(raw)
        if not isinstance(parsed, dict):
            raise ValueError("导演分镜结果必须是JSON对象。")

        shots = parsed.get("shots", [])
        if not isinstance(shots, list):
            raise ValueError("shots字段必须是数组。")

        self._validate_shots(shots)

        calculated_duration = sum(
            int(shot.get("duration", 0) or 0)
            for shot in shots
        )
        episode_title = str(
            parsed.get("episode_title") or "未命名分镜"
        )

        return StoryboardResult(
            episode_title=episode_title,
            total_duration=calculated_duration,
            shots=shots,
            raw=raw,
        )

    def compile_video_prompts(
        self,
        storyboard: StoryboardResult,
        characters: list[dict[str, Any]],
        scenes: list[dict[str, Any]],
        props: list[dict[str, Any]],
    ) -> PromptCompileResult:
        context = {
            "storyboard": {
                "episode_title": storyboard.episode_title,
                "total_duration": storyboard.total_duration,
                "shots": storyboard.shots,
            },
            "character_assets": characters,
            "scene_assets": scenes,
            "prop_assets": props,
        }

        raw = self.router.chat(
            "prompt_compile",
            PROMPT_SYSTEM,
            PROMPT_USER
            + "\n\n导演资料：\n"
            + json.dumps(context, ensure_ascii=False),
            temperature=0.25,
        )

        parsed = extract_json(raw)
        if not isinstance(parsed, dict):
            raise ValueError("Prompt编译结果必须是JSON对象。")

        prompts = parsed.get("prompts", [])
        if not isinstance(prompts, list):
            raise ValueError("prompts字段必须是数组。")

        shot_ids = {
            str(shot.get("shot_id", ""))
            for shot in storyboard.shots
        }
        prompt_ids = {
            str(item.get("shot_id", ""))
            for item in prompts
        }

        missing = sorted(shot_ids - prompt_ids)
        if missing:
            raise ValueError(
                "以下镜头缺少视频Prompt："
                + "、".join(missing)
            )

        return PromptCompileResult(prompts=prompts, raw=raw)

    @staticmethod
    def _validate_shots(shots: list[dict[str, Any]]) -> None:
        if not shots:
            raise ValueError("模型没有生成任何镜头。")

        seen_ids: set[str] = set()
        for index, shot in enumerate(shots, start=1):
            if not isinstance(shot, dict):
                raise ValueError(f"第{index}个镜头不是JSON对象。")

            shot_id = str(shot.get("shot_id") or "").strip()
            if not shot_id:
                raise ValueError(f"第{index}个镜头缺少shot_id。")
            if shot_id in seen_ids:
                raise ValueError(f"镜头编号重复：{shot_id}")
            seen_ids.add(shot_id)

            duration = int(shot.get("duration", 0) or 0)
            if duration <= 0:
                raise ValueError(f"{shot_id}的duration必须大于0。")

            timeline = shot.get("action_timeline", [])
            if not isinstance(timeline, list) or not timeline:
                raise ValueError(f"{shot_id}缺少action_timeline。")
