"""LayoutView 빌더 헬퍼."""
from __future__ import annotations

import discord
from discord.ui import Container, LayoutView, Separator, TextDisplay

FOOTER_TEXT = "-# KEL Scrim Bot"


def _build(title: str, body: str, accent: discord.Color) -> LayoutView:
    view = LayoutView()
    view.add_item(
        Container(
            TextDisplay(content=f"## {title}\n{body}"),
            Separator(),
            TextDisplay(content=FOOTER_TEXT),
            accent_colour=accent,
        )
    )
    return view


def info_view(body: str, title: str = "ℹ️ 안내") -> LayoutView:
    return _build(title, body, discord.Color.blurple())


def success_view(body: str, title: str = "✅ 완료") -> LayoutView:
    return _build(title, body, discord.Color.green())


def error_view(body: str, title: str = "❌ 오류") -> LayoutView:
    return _build(title, body, discord.Color.red())


def warning_view(body: str, title: str = "⚠️ 확인") -> LayoutView:
    return _build(title, body, discord.Color.orange())
