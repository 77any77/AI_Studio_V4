from ai_studio.models.config import APISettings


def test_config_round_trip():
    settings = APISettings(
        provider="DeepSeek",
        base_url="https://api.deepseek.com/v1",
        api_key="test",
        model="deepseek-chat",
        timeout_seconds=90,
    )
    restored = APISettings.from_dict(settings.to_dict())
    assert restored == settings
