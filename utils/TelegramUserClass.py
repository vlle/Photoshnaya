from aiogram import types

class TelegramEntity():
    def __init__(self, username: str | None, full_name: str, telegram_id: int, message_id: int) -> None:
        if username is None:
            self.username = "n/e"
        else:
            self.username = username
        self.full_name = full_name
        self.telegram_id = telegram_id
        self.message_id = message_id


class TelegramUser(TelegramEntity):
    def __init__(self, username: str | None, full_name: str, telegram_id: int, chat_id: int, message_id: int) -> None:

        super().__init__(username, full_name, telegram_id, message_id)
        self.chat_id = chat_id


class TelegramChat(TelegramEntity):
    def __init__(self, username: str | None, full_name: str, telegram_id: int, message_id: int) -> None:
        super().__init__(username, full_name, telegram_id, message_id)

class TelegramDeserialize():
    @staticmethod
    def unpack(message: types.Message, message_id_not_exists=False):
        if (message_id_not_exists == True):
            user = TelegramUser(message.from_user.username, message.from_user.full_name, message.from_user.id, message.chat.id, -1)
            chat = TelegramChat(message.chat.username, message.chat.full_name, message.chat.id, -1)
        else:
            user = TelegramUser(message.from_user.username, message.from_user.full_name, message.from_user.id, message.chat.id, message.message_id)
            chat = TelegramChat(message.chat.username, message.chat.full_name, message.chat.id, message.message_id)
        return user, chat


class ApplicablePhoto():
    def __init__(self, file_id: str) -> None:
        self.file_id = file_id

class Photo(ApplicablePhoto):
    pass

class Document(ApplicablePhoto):
    pass
