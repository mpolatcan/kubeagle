"""Tests for CustomDigits widget."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from kubeagle.widgets.display.custom_digits import CustomDigits


def test_custom_digits_instantiation():
    """Test CustomDigits widget instantiation with various parameters."""
    digits = CustomDigits("123")
    assert digits is not None
    assert digits.value == "123"


def test_custom_digits_alignment():
    """Test alignment class application."""
    digits_left = CustomDigits("100", align="left")
    assert "align-left" in digits_left.classes

    digits_center = CustomDigits("200", align="center")
    assert "align-center" in digits_center.classes

    digits_right = CustomDigits("300", align="right")
    assert "align-right" in digits_right.classes


def test_custom_digits_disabled():
    """Test disabled state."""
    digits_disabled = CustomDigits("700", disabled=True)
    assert digits_disabled.disabled is True


def test_custom_digits_css_path():
    """Test CSS path is set correctly."""
    assert CustomDigits.CSS_PATH.endswith("css/widgets/custom_digits.tcss")


def test_custom_digits_with_id():
    """Test CustomDigits with ID."""
    digits = CustomDigits("123", id="digits-1")
    assert digits.id == "digits-1"


def test_custom_digits_emphasis_with_extra_classes():
    """Test emphasis + classes are applied as valid separate identifiers."""
    digits = CustomDigits("42", align="center", emphasis="muted", classes="my-class")
    assert "align-center" in digits.classes
    assert "muted" in digits.classes
    assert "my-class" in digits.classes


def test_custom_digits_update_with_animation_updates_value():
    """Animated update should still update the visible value."""
    digits = CustomDigits("1")
    digits.update_with_animation("2")
    assert digits.value == "2"


def test_custom_digits_animate_update_adds_and_clears_animation_class(
    monkeypatch: pytest.MonkeyPatch,
):
    """Animation helper should apply and clear transient CSS class via timer callback."""
    digits = CustomDigits("9")
    captured_interval = 0.0
    captured_callback: Callable[[], None] | None = None

    class _TimerStub:
        def stop(self) -> None:
            return None

    def _fake_set_timer(
        interval: float,
        callback: Callable[[], None],
    ) -> _TimerStub:
        nonlocal captured_interval, captured_callback
        captured_interval = interval
        captured_callback = callback
        return _TimerStub()

    monkeypatch.setattr(CustomDigits, "is_mounted", property(lambda self: True))
    monkeypatch.setattr(digits, "set_timer", _fake_set_timer)

    digits.animate_update(duration=0.25)

    assert "value-updated" in digits.classes
    assert captured_interval == 0.25

    assert captured_callback is not None
    captured_callback()
    assert "value-updated" not in digits.classes


def test_custom_digits_update_with_animation_counts_through_intermediate_values(
    monkeypatch: pytest.MonkeyPatch,
):
    """Mounted numeric updates should animate through intermediate counter steps."""
    digits = CustomDigits("0")
    callbacks: list[Callable[[], None]] = []

    class _TimerStub:
        def stop(self) -> None:
            return None

    def _fake_set_timer(
        interval: float,
        callback: Callable[[], None],
    ) -> _TimerStub:
        assert interval > 0
        callbacks.append(callback)
        return _TimerStub()

    monkeypatch.setattr(CustomDigits, "is_mounted", property(lambda self: True))
    monkeypatch.setattr(digits, "set_timer", _fake_set_timer)

    digits.update_with_animation("3", duration=0.2)
    assert callbacks

    seen_values = [digits.value]
    guard = 0
    while callbacks and guard < 20:
        cb = callbacks.pop(0)
        cb()
        seen_values.append(digits.value)
        guard += 1

    assert digits.value == "3"
    assert "1" in seen_values
    assert "2" in seen_values


def test_custom_digits_update_with_animation_counts_percentage_values(
    monkeypatch: pytest.MonkeyPatch,
):
    """Percentage updates should animate through intermediate percentage frames."""
    digits = CustomDigits("0%")
    callbacks: list[Callable[[], None]] = []

    class _TimerStub:
        def stop(self) -> None:
            return None

    def _fake_set_timer(
        interval: float,
        callback: Callable[[], None],
    ) -> _TimerStub:
        assert interval > 0
        callbacks.append(callback)
        return _TimerStub()

    monkeypatch.setattr(CustomDigits, "is_mounted", property(lambda self: True))
    monkeypatch.setattr(digits, "set_timer", _fake_set_timer)

    digits.update_with_animation("3%", duration=0.2)
    assert callbacks

    seen_values = [digits.value]
    guard = 0
    while callbacks and guard < 20:
        cb = callbacks.pop(0)
        cb()
        seen_values.append(digits.value)
        guard += 1

    assert digits.value == "3%"
    assert "1%" in seen_values
    assert "2%" in seen_values


def test_custom_digits_update_with_animation_skips_counter_for_emoji_high_precision(
    monkeypatch: pytest.MonkeyPatch,
):
    """Emoji + 3-decimal values should skip counter stepping to avoid visual jitter."""
    digits = CustomDigits("⚠️ 1.234%")
    callbacks: list[Callable[[], None]] = []

    class _TimerStub:
        def stop(self) -> None:
            return None

    def _fake_set_timer(
        interval: float,
        callback: Callable[[], None],
    ) -> _TimerStub:
        assert interval > 0
        callbacks.append(callback)
        return _TimerStub()

    monkeypatch.setattr(CustomDigits, "is_mounted", property(lambda self: True))
    monkeypatch.setattr(digits, "set_timer", _fake_set_timer)

    digits.update_with_animation("⚠️ 1.567%", duration=0.2)

    assert digits.value == "⚠️ 1.567%"
    # Pulse-only animation schedules one timer; counter animation would enqueue
    # extra frame timers for intermediate steps.
    assert len(callbacks) == 1


def test_custom_digits_update_with_animation_calls_on_complete_immediate_path() -> None:
    """on_complete should run when value updates without stepped counter animation."""
    digits = CustomDigits("N/A")
    callback_called = False

    def _on_complete() -> None:
        nonlocal callback_called
        callback_called = True

    digits.update_with_animation("Ready", on_complete=_on_complete)

    assert digits.value == "Ready"
    assert callback_called is True


def test_custom_digits_update_with_animation_calls_on_complete_after_counter(
    monkeypatch: pytest.MonkeyPatch,
):
    """on_complete should run only after the counter animation reaches target value."""
    digits = CustomDigits("0")
    callbacks: list[Callable[[], None]] = []
    callback_called = False

    class _TimerStub:
        def stop(self) -> None:
            return None

    def _fake_set_timer(
        interval: float,
        callback: Callable[[], None],
    ) -> _TimerStub:
        assert interval > 0
        callbacks.append(callback)
        return _TimerStub()

    def _on_complete() -> None:
        nonlocal callback_called
        callback_called = True

    monkeypatch.setattr(CustomDigits, "is_mounted", property(lambda self: True))
    monkeypatch.setattr(digits, "set_timer", _fake_set_timer)

    digits.update_with_animation("3", duration=0.2, on_complete=_on_complete)
    assert callback_called is False

    guard = 0
    while callbacks and guard < 20:
        cb = callbacks.pop(0)
        cb()
        guard += 1

    assert digits.value == "3"
    assert callback_called is True
