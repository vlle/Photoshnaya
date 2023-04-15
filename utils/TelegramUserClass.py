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

class ApplicablePhoto():
    def __init__(self, file_id: str) -> None:
        self.file_id = file_id

class Photo(ApplicablePhoto):
    pass

class Document(ApplicablePhoto):
    pass
