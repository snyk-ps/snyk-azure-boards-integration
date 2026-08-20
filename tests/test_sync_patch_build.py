"""Tests for sync JSON Patch helpers."""

from sync.patch_build import (
    _escape_and_linkify_plain_text,
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


def test_build_create_patch_uses_custom_description_field() -> None:
    ops = build_create_patch(
        title="T",
        description="Body",
        active_state="New",
        template={},
        description_field="Microsoft.VSTS.TCM.ReproSteps",
    )
    desc_op = next(
        o for o in ops if o.get("path") == "/fields/Microsoft.VSTS.TCM.ReproSteps"
    )
    assert desc_op["value"] == "<p>Body</p>"
    assert not any(o.get("path") == "/fields/System.Description" for o in ops)


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


def test_build_create_patch_includes_area_path_and_csv_assignee() -> None:
    tpl = {
        "json_patch": [
            {"op": "add", "path": "/fields/System.AssignedTo", "value": "template@example.com"},
        ],
    }
    ops = build_create_patch(
        title="T",
        description="D",
        active_state="New",
        template=tpl,
        area_path="MyProject\\TeamA",
        assigned_to="csv@example.com",
    )
    paths = [o["path"] for o in ops]
    assert "/fields/System.AreaPath" in paths
    assignee_ops = [o for o in ops if o.get("path") == "/fields/System.AssignedTo"]
    assert len(assignee_ops) == 1
    assert assignee_ops[0]["value"] == "csv@example.com"


def test_build_update_patch_area_path_and_csv_assignee() -> None:
    from sync.patch_build import build_update_patch

    ops = build_update_patch(
        title="T",
        description="D",
        state="Active",
        template={},
        area_path="New\\Path",
        patch_area_path=True,
        assigned_to="csv@example.com",
    )
    paths = [o["path"] for o in ops]
    assert "/fields/System.AreaPath" in paths
    assert any(
        o.get("path") == "/fields/System.AssignedTo" and o.get("value") == "csv@example.com"
        for o in ops
    )


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


def test_escape_and_linkify_plain_text_https_url() -> None:
    out = _escape_and_linkify_plain_text(
        "Access request: https://example.com/request-snyk-access",
    )
    assert '<a href="https://example.com/request-snyk-access">' in out
    assert "Access request:" in out


def test_escape_and_linkify_strips_trailing_period_from_href() -> None:
    out = _escape_and_linkify_plain_text("See https://example.com/path.")
    assert 'href="https://example.com/path"' in out
    assert out.endswith(".")


def test_escape_and_linkify_cve_nvd_url_in_parens() -> None:
    plain = "CVE-2023-29017 (https://nvd.nist.gov/vuln/detail/CVE-2023-29017)"
    out = _escape_and_linkify_plain_text(plain)
    assert "CVE-2023-29017" in out
    assert '<a href="https://nvd.nist.gov/vuln/detail/CVE-2023-29017">' in out
    assert out.endswith(")")


def test_escape_and_linkify_escapes_ampersand_outside_urls() -> None:
    out = _escape_and_linkify_plain_text("x & y https://example.com")
    assert "&amp;" in out
    assert "<a href=" in out


def test_escape_and_linkify_does_not_linkify_javascript_scheme() -> None:
    out = _escape_and_linkify_plain_text("javascript:alert(1)")
    assert "<a href=" not in out
    assert "javascript:alert(1)" in out


def test_build_create_patch_open_in_snyk_keeps_view_in_snyk_label() -> None:
    url = "https://app.snyk.io/org/acme/project/p#issue-SNYK-1"
    plain = f"Open in Snyk\n{url}\n\nExtra note"
    ops = build_create_patch(
        title="T",
        description=plain,
        active_state="New",
        template={},
    )
    desc_op = next(o for o in ops if o.get("path") == "/fields/System.Description")
    val = desc_op["value"]
    assert 'view in Snyk</a>' in val
    assert f'href="{url}"' in val
    assert f">{url}</a>" not in val


def test_build_create_patch_open_in_snyk_regional_app_base() -> None:
    url = "https://app.eu.snyk.io/org/acme/project/p#issue-SNYK-1"
    plain = f"Open in Snyk\n{url}"
    ops = build_create_patch(
        title="T",
        description=plain,
        active_state="New",
        template={},
        app_base_url="https://app.eu.snyk.io",
    )
    desc_op = next(o for o in ops if o.get("path") == "/fields/System.Description")
    assert 'view in Snyk</a>' in desc_op["value"]
    assert f'href="{url}"' in desc_op["value"]


def test_build_create_patch_appendix_url_is_hyperlink() -> None:
    ops = build_create_patch(
        title="T",
        description="Finding details\n\nAccess request:\nhttps://example.com/access",
        active_state="New",
        template={},
    )
    desc_op = next(o for o in ops if o.get("path") == "/fields/System.Description")
    assert '<a href="https://example.com/access">' in desc_op["value"]
