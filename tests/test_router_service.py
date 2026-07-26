from ai_studio.models.config import APIProfile, AppSettings
from ai_studio.services.router_service import APIRouterService


def test_router_selects_profile_for_task():
    analysis = APIProfile(name="分析接口")
    storyboard = APIProfile(name="分镜接口")
    settings = AppSettings(
        profiles=[analysis, storyboard],
        task_routes={
            "story_analysis": analysis.profile_id,
            "storyboard": storyboard.profile_id,
        },
    )

    router = APIRouterService(settings)

    assert router.profile_for("story_analysis").name == "分析接口"
    assert router.profile_for("storyboard").name == "分镜接口"
