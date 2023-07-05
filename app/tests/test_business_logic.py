import pytest
import random
from app.handlers.user_action import is_valid_input

from app.utils.TelegramUserClass import TelegramChat, TelegramUser


async def test_is_hashtags_registered_correctly():
    user = TelegramUser("Random", "Random Full", 123, 12, 1)
    chat = TelegramChat("lorem", "ipsum", 1, 1, "group")
    theme = "#test_theme"
    punctuation = """!"#$%&'()*+,-./:;<=>?@[]\\^_`{|}~"""
    captions = [theme + random.choice(punctuation) for _ in range(10)]
    for caption in captions:
        assert await is_valid_input(caption, theme, chat, user) is True

    assert await is_valid_input("test_theme", theme, chat, user) is False
    assert await is_valid_input("#test_theme", theme, chat, user) is True
