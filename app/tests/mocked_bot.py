"""Минимальный offline-двойник Bot для e2e-тестов.

aiogram 3.0.0b7 не поставляет тестовых утилит, поэтому свой `BaseSession`,
который не ходит в сеть, а складывает исходящие методы (SendPhoto,
EditMessageMedia, AnswerCallbackQuery, ...) в список для ассертов.

Bot резолвится хендлерами через contextvar `Bot.set_current`, который
ставит `Dispatcher.feed_update`, — поэтому `message.answer` /
`query.message.edit_media` находят именно этот бот без ручного биндинга.
"""
from __future__ import annotations

from typing import Any

from aiogram import Bot
from aiogram.client.session.base import BaseSession
from aiogram.methods import TelegramMethod

# 35+ символов после двоеточия — иначе Bot не примет токен.
TEST_TOKEN = "42:TESTTESTTESTTESTTESTTESTTESTTESTTEST"


class MockedSession(BaseSession):
    def __init__(self) -> None:
        super().__init__()
        self.requests: list[TelegramMethod[Any]] = []

    async def close(self) -> None:
        pass

    async def make_request(self, bot, method, timeout=None):
        self.requests.append(method)
        return None

    async def stream_content(
        self, url, headers=None, timeout=30, chunk_size=65536, raise_for_status=True
    ):
        yield b""


class MockedBot(Bot):
    def __init__(self) -> None:
        super().__init__(token=TEST_TOKEN, session=MockedSession())

    @property
    def requests(self) -> list[TelegramMethod[Any]]:
        return self.session.requests  # type: ignore[attr-defined]

    def sent(self, method_name: str) -> list[TelegramMethod[Any]]:
        """Все перехваченные вызовы данного типа, напр. sent("SendPhoto")."""
        return [r for r in self.requests if type(r).__name__ == method_name]

    def sent_names(self) -> list[str]:
        return [type(r).__name__ for r in self.requests]

    def clear(self) -> None:
        self.requests.clear()
