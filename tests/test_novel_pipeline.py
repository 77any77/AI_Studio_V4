from ai_studio.services.novel_pipeline import NovelPipeline


class FakeRouter:
    def chat(self, task_key, system, user, temperature=0.2):
        values = {
            "story_analysis": '{"title":"测试","story_beats":[]}',
            "character_extract": '{"characters":[{"name":"林然"}]}',
            "scene_extract": '{"scenes":[{"name":"办公室"}]}',
            "prop_extract": '{"props":[{"name":"手机"}]}',
        }
        return values[task_key]


def test_full_pipeline():
    result = NovelPipeline(FakeRouter()).run_all("测试小说")
    assert result.analysis["title"] == "测试"
    assert result.characters[0]["name"] == "林然"
    assert result.scenes[0]["name"] == "办公室"
    assert result.props[0]["name"] == "手机"
