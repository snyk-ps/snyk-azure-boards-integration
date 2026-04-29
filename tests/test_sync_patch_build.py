"""Tests for sync JSON Patch helpers."""

from sync.patch_build import (
    build_create_patch,
    filter_assignee_from_create_patch,
    template_supplies_assigned_to,
)


def test_template_supplies_assigned_to_false() -> None:
    assert template_supplies_assigned_to({}) is False


def test_template_supplies_assigned_to_true() -> None:
    tpl = {
        "json_patch": [
            {"op": "add", "path": "/fields/System.AssignedTo", "value": "x"},
        ],
    }
    assert template_supplies_assigned_to(tpl) is True


def test_filter_assignee_removes_assigned_to_when_not_supplied() -> None:
    ops = [
        {"op": "add", "path": "/fields/System.Title", "value": "t"},
        {"op": "add", "path": "/fields/System.AssignedTo", "value": "u"},
    ]
    out = filter_assignee_from_create_patch(ops, template_supplies_assignee=False)
    assert len(out) == 1
    assert out[0]["path"] == "/fields/System.Title"


def test_build_create_patch_includes_tags_and_template_ops() -> None:
    tpl = {
        "tags": ["Snyk", "security"],
        "json_patch": [
            {"op": "add", "path": "/fields/Custom.Field", "value": 1},
        ],
    }
    ops = build_create_patch(
        title="T",
        description="D",
        active_state="New",
        template=tpl,
    )
    paths = [o["path"] for o in ops]
    assert "/fields/System.Title" in paths
    assert "/fields/System.Tags" in paths
    assert "/fields/Custom.Field" in paths
    desc_op = next(o for o in ops if o.get("path") == "/fields/System.Description")
    assert desc_op["value"] == "<p>D</p>"


def test_build_create_patch_description_html_paragraph_breaks() -> None:
    ops = build_create_patch(
        title="T",
        description="First block\n\nSecond block",
        active_state="New",
        template={},
    )
    desc_op = next(o for o in ops if o.get("path") == "/fields/System.Description")
    v = desc_op["value"]
    assert v.count("<p>") == 2
    assert "First block" in v
    assert "Second block" in v
