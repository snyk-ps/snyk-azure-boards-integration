"""Tests for ``config.template_merge``."""

from config.template_merge import merge_work_item_templates


def test_merge_json_patch_concat_order() -> None:
    out = merge_work_item_templates(
        {"json_patch": [{"op": "add", "path": "/fields/a", "value": "1"}]},
        {"json_patch": [{"op": "add", "path": "/fields/b", "value": "2"}]},
        {"json_patch": [{"op": "add", "path": "/fields/c", "value": "3"}]},
    )
    assert len(out["json_patch"]) == 3
    assert out["json_patch"][0]["path"] == "/fields/a"
    assert out["json_patch"][2]["path"] == "/fields/c"


def test_merge_tags_dedupe_order() -> None:
    out = merge_work_item_templates(
        {"tags": ["a", "b"]},
        {"tags": ["b", "c"]},
        {"tags": ["c"]},
    )
    assert out["tags"] == ["a", "b", "c"]


def test_merge_other_keys_last_wins() -> None:
    out = merge_work_item_templates({"x": 1}, {"x": 2}, {"x": 3})
    assert out["x"] == 3
