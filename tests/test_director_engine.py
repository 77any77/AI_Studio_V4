from ai_studio.services.director_engine import (
    DirectorEngine,
    StoryboardResult,
)


class FakeRouter:
    def chat(self, task_key, system, user, temperature=0.2):
        if task_key == "storyboard":
            return """{
              "episode_title": "测试",
              "total_duration": 8,
              "shots": [
                {
                  "shot_id": "S001",
                  "duration": 8,
                  "action_timeline": [
                    {"time": "0-8秒", "action": "人物抬头"}
                  ]
                }
              ]
            }"""
        if task_key == "prompt_compile":
            return """{
              "prompts": [
                {
                  "shot_id": "S001",
                  "duration": 8,
                  "prompt": "测试提示词",
                  "negative_prompt": "避免变形",
                  "continuity_reference": "承接上一镜"
                }
              ]
            }"""
        raise KeyError(task_key)


def test_create_storyboard():
    engine = DirectorEngine(FakeRouter())
    result = engine.create_storyboard(
        novel="小说",
        analysis={},
        characters=[],
        scenes=[],
        props=[],
    )
    assert result.episode_title == "测试"
    assert result.total_duration == 8
    assert result.shots[0]["shot_id"] == "S001"


def test_compile_prompts():
    engine = DirectorEngine(FakeRouter())
    storyboard = StoryboardResult(
        episode_title="测试",
        total_duration=8,
        shots=[
            {
                "shot_id": "S001",
                "duration": 8,
                "action_timeline": [
                    {"time": "0-8秒", "action": "人物抬头"}
                ],
            }
        ],
        raw="",
    )
    result = engine.compile_video_prompts(
        storyboard=storyboard,
        characters=[],
        scenes=[],
        props=[],
    )
    assert result.prompts[0]["prompt"] == "测试提示词"
