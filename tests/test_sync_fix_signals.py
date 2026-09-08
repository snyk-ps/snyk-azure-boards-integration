"""Tests for fix-availability signals read across all issue coordinates (P2-FR-5.5)."""

from typing import Any

import pytest

from sync.fix_signals import FIX_SIGNAL_KEYS, FIX_SIGNAL_LABELS, true_fix_signal_keys
from sync.issue_content import fix_signal_labels
from sync.issue_filters import attrs_indicate_fix_available


def _coord(**flags: Any) -> dict[str, Any]:
    """Coordinate with every recognized signal false unless overridden."""
    coord: dict[str, Any] = {key: False for key in FIX_SIGNAL_KEYS}
    coord.update(flags)
    return coord


# --- shared constant matches the spec -------------------------------------


def test_signal_keys_match_p2_fr_5_5_list() -> None:
    assert FIX_SIGNAL_KEYS == (
        "is_upgradeable",
        "is_patchable",
        "is_fixable_manually",
        "is_fixable_snyk",
        "is_fixable_upstream",
    )


def test_is_pinnable_is_not_a_recognized_signal() -> None:
    assert "is_pinnable" not in FIX_SIGNAL_KEYS
    assert "is_pinnable" not in FIX_SIGNAL_LABELS


def test_labels_cover_every_key() -> None:
    assert tuple(FIX_SIGNAL_LABELS) == FIX_SIGNAL_KEYS


# --- true_fix_signal_keys --------------------------------------------------


def test_signal_on_first_coordinate() -> None:
    attrs = {"coordinates": [_coord(is_upgradeable=True), _coord()]}
    assert true_fix_signal_keys(attrs) == ["is_upgradeable"]


def test_signal_only_on_later_coordinate() -> None:
    attrs = {"coordinates": [_coord(), _coord(), _coord(is_patchable=True)]}
    assert true_fix_signal_keys(attrs) == ["is_patchable"]


def test_signals_across_several_coordinates_are_unioned() -> None:
    attrs = {
        "coordinates": [
            _coord(is_fixable_upstream=True),
            _coord(is_upgradeable=True),
            _coord(is_upgradeable=True),
        ],
    }
    assert true_fix_signal_keys(attrs) == ["is_upgradeable", "is_fixable_upstream"]


def test_result_follows_declaration_order_not_payload_order() -> None:
    attrs = {
        "coordinates": [
            _coord(is_fixable_upstream=True),
            _coord(is_fixable_snyk=True),
            _coord(is_patchable=True),
        ],
    }
    assert true_fix_signal_keys(attrs) == [
        "is_patchable",
        "is_fixable_snyk",
        "is_fixable_upstream",
    ]


def test_no_signal_on_any_coordinate() -> None:
    attrs = {"coordinates": [_coord(), _coord()]}
    assert true_fix_signal_keys(attrs) == []


@pytest.mark.parametrize(
    "attrs",
    [
        {},
        {"coordinates": []},
        {"coordinates": None},
        {"coordinates": "not-a-list"},
        {"coordinates": {"is_upgradeable": True}},
    ],
    ids=["absent", "empty", "none", "string", "mapping"],
)
def test_missing_or_malformed_coordinates_yield_no_signals(attrs: dict[str, Any]) -> None:
    assert true_fix_signal_keys(attrs) == []


def test_non_dict_entries_are_skipped() -> None:
    attrs = {"coordinates": ["nonsense", None, 7, _coord(is_patchable=True)]}
    assert true_fix_signal_keys(attrs) == ["is_patchable"]


@pytest.mark.parametrize("value", ["true", 1, [1], {"a": 1}], ids=["str", "int", "list", "dict"])
def test_truthy_but_not_true_values_are_rejected(value: Any) -> None:
    attrs = {"coordinates": [{"is_upgradeable": value}]}
    assert true_fix_signal_keys(attrs) == []


def test_is_pinnable_alone_yields_no_signals() -> None:
    attrs = {"coordinates": [_coord(is_pinnable=True)]}
    assert true_fix_signal_keys(attrs) == []


# --- attrs_indicate_fix_available (create gate) ----------------------------


def test_gate_true_when_signal_on_first_coordinate() -> None:
    attrs = {"coordinates": [_coord(is_upgradeable=True)]}
    assert attrs_indicate_fix_available(attrs) is True


def test_gate_true_when_signal_only_on_later_coordinate() -> None:
    attrs = {"coordinates": [_coord(), _coord(is_fixable_snyk=True)]}
    assert attrs_indicate_fix_available(attrs) is True


def test_gate_false_when_no_coordinate_has_a_signal() -> None:
    attrs = {"coordinates": [_coord(), _coord()]}
    assert attrs_indicate_fix_available(attrs) is False


def test_gate_false_when_only_pinnable() -> None:
    attrs = {"coordinates": [_coord(is_pinnable=True)]}
    assert attrs_indicate_fix_available(attrs) is False


@pytest.mark.parametrize(
    "attrs",
    [{}, {"coordinates": []}, {"coordinates": "x"}],
    ids=["absent", "empty", "non-list"],
)
def test_gate_false_for_missing_or_malformed_coordinates(attrs: dict[str, Any]) -> None:
    assert attrs_indicate_fix_available(attrs) is False


def test_gate_tolerates_malformed_entries_without_raising() -> None:
    attrs = {"coordinates": [None, _coord(is_patchable=True)]}
    assert attrs_indicate_fix_available(attrs) is True


# --- fix_signal_labels (description summary) -------------------------------


def test_labels_unioned_across_coordinates_without_duplication() -> None:
    attrs = {
        "coordinates": [
            _coord(is_upgradeable=True),
            _coord(is_upgradeable=True, is_patchable=True),
        ],
    }
    assert fix_signal_labels(attrs) == ["Upgrade available", "Patch available"]


def test_label_sourced_from_later_coordinate() -> None:
    attrs = {"coordinates": [_coord(), _coord(is_fixable_manually=True)]}
    assert fix_signal_labels(attrs) == ["Manual remediation possible"]


def test_label_order_is_stable_regardless_of_payload_order() -> None:
    forward = {"coordinates": [_coord(is_upgradeable=True), _coord(is_fixable_snyk=True)]}
    reverse = {"coordinates": [_coord(is_fixable_snyk=True), _coord(is_upgradeable=True)]}
    assert fix_signal_labels(forward) == fix_signal_labels(reverse)
    assert fix_signal_labels(forward) == [
        "Upgrade available",
        "Automated fix available via Snyk",
    ]


def test_labels_omit_pinnable() -> None:
    attrs = {"coordinates": [_coord(is_pinnable=True)]}
    assert fix_signal_labels(attrs) == []


def test_labels_empty_when_no_signals() -> None:
    assert fix_signal_labels({"coordinates": [_coord()]}) == []
    assert fix_signal_labels({}) == []
