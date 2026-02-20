"""Tests for CustomRule widget."""

from __future__ import annotations

from kubeagle.widgets.structure.custom_rule import CustomRule


def test_custom_rule_instantiation():
    """Test CustomRule instantiation."""
    rule = CustomRule()
    assert rule is not None
    assert rule._line_style == "solid"
    assert rule._orientation == "horizontal"


def test_custom_rule_with_line_style():
    """Test CustomRule with line style."""
    rule_dashed = CustomRule(line_style="dashed")
    assert rule_dashed._line_style == "dashed"

    rule_dotted = CustomRule(line_style="dotted")
    assert rule_dotted._line_style == "dotted"


def test_custom_rule_with_orientation():
    """Test CustomRule with orientation."""
    rule_vertical = CustomRule(orientation="vertical")
    assert rule_vertical._orientation == "vertical"


def test_custom_rule_disabled():
    """Test CustomRule disabled state."""
    rule_disabled = CustomRule(disabled=True)
    assert rule_disabled._disabled is True


def test_custom_rule_css_path():
    """Test CSS path is set correctly."""
    assert CustomRule.CSS_PATH.endswith("css/widgets/custom_rule.tcss")


def test_custom_rule_with_id():
    """Test CustomRule with ID."""
    rule = CustomRule(id="rule-1")
    assert rule.id == "rule-1"


def test_custom_rule_with_classes():
    """Test CustomRule with classes."""
    rule = CustomRule(classes="custom-class")
    assert "custom-class" in rule.classes
