from ai_studio.models.config import APIProfile
from ai_studio.services.api_client import OpenAICompatibleClient


def test_endpoint_building():
    client = OpenAICompatibleClient(
        APIProfile(base_url="https://example.com/v1")
    )
    assert client.endpoint() == "https://example.com/v1/chat/completions"


def test_endpoint_not_duplicated():
    client = OpenAICompatibleClient(
        APIProfile(base_url="https://example.com/v1/chat/completions")
    )
    assert client.endpoint() == "https://example.com/v1/chat/completions"


def test_empty_base_url_is_rejected():
    client = OpenAICompatibleClient(APIProfile(base_url=""))
    try:
        client.endpoint()
    except Exception as exc:
        assert "Base URL" in str(exc)
    else:
        raise AssertionError("空 Base URL 应该报错")
