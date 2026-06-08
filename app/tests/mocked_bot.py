"""Минимальный offline-двойник Bot для e2e-тестов.

aiogram 3.0.0b7 не поставляет тестовых утилит, поэтому свой `BaseSession`,
который не ходит в сеть, а складывает исходящие методы (SendPhoto,
EditMessageMedia, AnswerCallbackQuery, ...) в список для ассертов.

Bot резолвится хендлерами через contextvar `Bot.set_current`, который
ставит `Dispatcher.feed_update`, — поэтому `message.answer` /
`query.message.edit_media` находят именно этот бот без ручного биндинга.

Методы, чей РЕЗУЛЬТАТ потребляется хендлером (`bot.me()`, `get_chat_member`,
`send_*().message_id`, `send_photo().get_url()`, `copy_message()`), получают
каноничные ответы по умолчанию; тест может переопределить любой через
`MockedBot(responses=...)` или `bot.set_response("GetChatMember", value)`.
Значение — либо готовый объект, либо callable(method) -> объект.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

from aiogram import Bot
from aiogram.client.session.base import BaseSession
from aiogram.methods import TelegramMethod
from aiogram.types import Chat, ChatMemberMember, Message, User

# 35+ символов после двоеточия — иначе Bot не примет токен.
TEST_TOKEN = "42:TESTTESTTESTTESTTESTTESTTESTTESTTEST"

BOT_USER = User(id=42, is_bot=True, first_name="bot", username="testbot")

# Методы, чей результат хендлеры читают как Message (.message_id / .get_url()).
_MESSAGE_RETURNING = frozenset(
    {"SendMessage", "SendPhoto", "SendDocument", "CopyMessage", "ForwardMessage"}
)
_TRUE_RETURNING = frozenset({"PinChatMessage", "AnswerCallbackQuery", "DeleteMessage"})


def _coerce_chat_id(raw: Any) -> int:
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str) and raw.lstrip("-").isdigit():
        return int(raw)
    return 1


class MockedSession(BaseSession):
    def __init__(self, responses: dict[str, Any] | None = None) -> None:
        super().__init__()
        self.requests: list[TelegramMethod[Any]] = []
        self.responses: dict[str, Any] = dict(responses or {})
        self._mid = 5000

    async def close(self) -> None:
        pass

    async def make_request(self, bot, method, timeout=None):
        self.requests.append(method)
        name = type(method).__name__
        if name in self.responses:
            override = self.responses[name]
            return override(method) if callable(override) else override
        return self._default_response(method, name)

    def _default_response(self, method: TelegramMethod[Any], name: str) -> Any:
        if name == "GetMe":
            return BOT_USER
        if name == "GetChatMember":
            return ChatMemberMember(
                user=User(
                    id=getattr(method, "user_id", 1) or 1,
                    is_bot=False,
                    first_name="member",
                )
            )
        if name == "SendMediaGroup":
            return []
        if name in _MESSAGE_RETURNING:
            return self._fake_message(method)
        if name in _TRUE_RETURNING:
            return True
        return None

    def _fake_message(self, method: TelegramMethod[Any]) -> Message:
        self._mid += 1
        raw_chat = getattr(method, "chat_id", None)
        if raw_chat is None:
            raw_chat = getattr(method, "from_chat_id", 1)
        return Message(
            message_id=self._mid,
            date=datetime.now(timezone.utc),
            chat=Chat(id=_coerce_chat_id(raw_chat), type="private"),
            from_user=BOT_USER,
        )

    async def stream_content(
        self, url, headers=None, timeout=30, chunk_size=65536, raise_for_status=True
    ):
        yield b""


class MockedBot(Bot):
    def __init__(self, responses: dict[str, Any] | None = None) -> None:
        super().__init__(token=TEST_TOKEN, session=MockedSession(responses))

    @property
    def requests(self) -> list[TelegramMethod[Any]]:
        return self.session.requests  # type: ignore[attr-defined]

    def set_response(self, method_name: str, value: Any | Callable[[Any], Any]) -> None:
        """Переопределить ответ на конкретный метод (объект или callable(method))."""
        self.session.responses[method_name] = value  # type: ignore[attr-defined]

    def sent(self, method_name: str) -> list[TelegramMethod[Any]]:
        """Все перехваченные вызовы данного типа, напр. sent("SendPhoto")."""
        return [r for r in self.requests if type(r).__name__ == method_name]

    def sent_names(self) -> list[str]:
        return [type(r).__name__ for r in self.requests]

    def clear(self) -> None:
        self.requests.clear()
