"""Rich terminal rendering for Strands :class:`~strands.agent.agent.Agent` callbacks."""

from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule


class RichAgentConsoleCallback:
    """Stream assistant text as Markdown (via :class:`~rich.live.Live`) and style tool banners.

    Compatible with Strands' ``PrintingCallbackHandler`` callback shape. Set
    ``_rich_agent_console`` so the Neuuf CLI can suppress duplicate ``print(result)``.
    """

    _rich_agent_console = True

    def __init__(self, *, verbose_tool_use: bool = True) -> None:
        self.console = Console(highlight=False, soft_wrap=True)
        self._verbose_tool_use = verbose_tool_use
        self.tool_count = 0
        self._buffer = ""
        self._live: Live | None = None

    def _stop_live(self) -> None:
        if self._live is not None:
            try:
                self._live.stop()
            finally:
                self._live = None

    def _start_live_if_needed(self) -> None:
        if self._live is None:
            self._live = Live(
                Markdown(""),
                console=self.console,
                refresh_per_second=15,
                transient=False,
                vertical_overflow="visible",
            )
            self._live.start(refresh=True)

    def __call__(self, **kwargs: Any) -> None:
        if kwargs.get("result") is not None:
            self._stop_live()
            self._buffer = ""
            return

        reasoning = kwargs.get("reasoningText", False)
        if reasoning:
            self._stop_live()
            self._buffer = ""
            self.console.print(
                Panel(
                    str(reasoning),
                    title="Reasoning",
                    border_style="magenta",
                    expand=False,
                )
            )

        data = kwargs.get("data", "")
        complete = kwargs.get("complete", False)
        event = kwargs.get("event") or {}
        tool_use: dict[str, Any] | None = None
        if isinstance(event, dict):
            raw = event.get("contentBlockStart", {})
            if isinstance(raw, dict):
                start = raw.get("start", {})
                if isinstance(start, dict):
                    tu = start.get("toolUse")
                    tool_use = tu if isinstance(tu, dict) else None

        if data:
            self._buffer += str(data)
            self._start_live_if_needed()
            if self._live is not None:
                self._live.update(Markdown(self._buffer))

        if tool_use:
            self._stop_live()
            self._buffer = ""
            self.tool_count += 1
            if self._verbose_tool_use:
                name = str(tool_use.get("name", "?"))
                self.console.print(
                    Rule(f"[bold cyan]Tool #{self.tool_count}[/]  [yellow]{name}[/]", style="cyan")
                )

        if complete and data:
            self.console.print()
