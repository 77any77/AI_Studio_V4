from ai_studio.models.config import APISettings
from ai_studio.services.api_client import OpenAICompatibleClient


def test_endpoint_building():
    client = OpenAICompatibleClient(
        APISettings(base_url="https://example.com/v1")
    )
    assert client.endpoint() == "https://example.com/v1/chat/completions"


def test_endpoint_not_duplicated():
    client = OpenAICompatibleClient(
        APISettings(base_url="https://example.com/v1/chat/completions")
    )
    assert client.endpoint() == "https://example.com/v1/chat/completions"
