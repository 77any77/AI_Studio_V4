from ai_studio.services.update_service import compare_versions, normalize_version


def test_normalize_version():
    assert normalize_version("v0.6.0") == (0, 6, 0)


def test_compare_versions():
    assert compare_versions("0.6.0", "0.5.0") == 1
    assert compare_versions("v1.0.0", "1.0") == 0
    assert compare_versions("0.9.9", "1.0.0") == -1
