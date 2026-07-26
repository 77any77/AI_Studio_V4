from ai_studio.models.config import (
    APIProfile,
    AppSettings,
    TASK_LABELS,
)


def test_profile_round_trip():
    profile = APIProfile(
        name="DeepSeek 主接口",
        provider="DeepSeek",
        base_url="https://api.deepseek.com/v1",
        api_key="secret",
        model="deepseek-chat",
        timeout_seconds=90,
    )
    restored = APIProfile.from_dict(profile.to_dict())
    assert restored == profile


def test_multi_api_routes_round_trip():
    first = APIProfile(name="分析模型")
    second = APIProfile(name="分镜模型")
    settings = AppSettings(
        profiles=[first, second],
        task_routes={
            task: (
                second.profile_id
                if task == "storyboard"
                else first.profile_id
            )
            for task in TASK_LABELS
        },
    )
    restored = AppSettings.from_dict(settings.to_dict())
    assert len(restored.profiles) == 2
    assert restored.profile_for_task("storyboard").name == "分镜模型"
    assert restored.profile_for_task("story_analysis").name == "分析模型"


def test_old_single_api_config_migration():
    restored = AppSettings.from_dict({
        "provider": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
        "api_key": "old-key",
        "model": "deepseek-chat",
        "timeout_seconds": 100,
    })
    assert len(restored.profiles) == 1
    assert restored.profiles[0].provider == "DeepSeek"
    assert restored.profile_for_task("storyboard").profile_id == (
        restored.profiles[0].profile_id
    )
