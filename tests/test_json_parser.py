from ai_studio.services.json_parser import extract_json


def test_extract_plain_json():
    assert extract_json('{"name":"test"}') == {"name": "test"}


def test_extract_markdown_json():
    value = extract_json('```json\n{"name":"test"}\n```')
    assert value == {"name": "test"}


def test_extract_json_with_explanation():
    value = extract_json('结果如下：\n{"items":[1,2]}\n完成')
    assert value == {"items": [1, 2]}
