"""Tests for Rich Strands callback (no live model)."""

from __future__ import annotations

from iso_agent.l3_runtime.cli.rich_agent_callback import RichAgentConsoleCallback


def test_rich_callback_marks_console_flag() -> None:
    cb = RichAgentConsoleCallback()
    assert getattr(cb, "_rich_agent_console") is True


def test_rich_callback_handles_result_without_raising() -> None:
    cb = RichAgentConsoleCallback()
    cb(data="partial", complete=False)
    cb(result=object())


def test_rich_callback_tool_use_increments_and_resets_buffer() -> None:
    cb = RichAgentConsoleCallback()
    cb(data="Hello ", complete=False)
    cb(
        data="world",
        complete=True,
        event={"contentBlockStart": {"start": {"toolUse": {"name": "calculator"}}}},
    )
    assert cb.tool_count == 1
