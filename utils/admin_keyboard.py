from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters.callback_data import CallbackData


class CallbackManage(CallbackData, prefix="adm"):
    user: str
    action: str
    group_id: str


class AdminActions:
    finish_contest_text = "Завершить голосование"
    finish_contest_id = '1'
    view_votes_text = "Посмотреть текущие голоса"
    view_votes_id = '2'
    view_submissions_text = "Посмотреть зарегистрированные фотографии"
    view_submissions_id = '3'


class AdminKeyboardButtons:
    def __init__(self, user: str, group_id: str) -> None:
        self.actions = AdminActions()
        self.finish_contest = InlineKeyboardButton(
                text=self.actions.finish_contest_text,
                callback_data=CallbackManage(user=user,
                                           action=self.
                                           actions.finish_contest_id,
                                           group_id=group_id).pack()
                )
        self.view_votes = InlineKeyboardButton(
                text=self.actions.view_votes_text,
                callback_data=CallbackManage(user=user,
                                           action=self.
                                           actions.view_votes_id,
                                           group_id=group_id).pack()
                )
        self.view_submissions = InlineKeyboardButton(
                text=self.actions.view_submissions_text,
                callback_data=CallbackManage(user=user,
                                           action=self.
                                           actions.view_submissions_id,
                                           group_id=group_id).pack()
                )


class AdminKeyboard:
    def __init__(self, user: str, group_id: str) -> None:
        self.buttons = AdminKeyboardButtons(user, group_id)
        self.keyboard_start = InlineKeyboardMarkup(
                inline_keyboard=
                [
                    [self.buttons.finish_contest],
                    [self.buttons.view_votes],
                    [self.buttons.view_submissions]
                    ]
                )
