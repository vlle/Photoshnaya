from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters.callback_data import CallbackData


class CallbackManage(CallbackData, prefix="adm"):
    user: str
    action: str
    msg_id: str
    group_id: str


class AdminActions:
    chosen_group = 'cg'
    finish_contest_text = "Начать голосование 🗳"
    finish_contest_id = '1'
    finish_vote_text = "Завершить голосование 🗳"
    finish_vote_id = '2'
    view_votes_text = "Посмотреть текущие голоса"
    view_votes_id = '3'
    view_submissions_text = "Посмотреть зарегистрированные фотографии"
    view_submissions_id = '3'
    back = 'b'
    back_text = 'Назад'


class AdminKeyboardButtons:
    def __init__(self, user: str, msg_id: str, group_id: str) -> None:
        self.actions = AdminActions()
        self.finish_contest = InlineKeyboardButton(
                text=self.actions.finish_contest_text,
                callback_data=CallbackManage(user=user,
                                             action=self.
                                             actions.finish_contest_id,
                                             msg_id=msg_id,
                                             group_id=group_id).pack()
                )
        self.finish_vote = InlineKeyboardButton(
                text=self.actions.finish_vote_text,
                callback_data=CallbackManage(user=user,
                                             action=self.
                                             actions.finish_vote_id,
                                             msg_id=msg_id,
                                             group_id=group_id).pack()
                )
        self.view_votes = InlineKeyboardButton(
                text=self.actions.view_votes_text,
                callback_data=CallbackManage(user=user,
                                             action=self.
                                             actions.view_votes_id,
                                             msg_id=msg_id,
                                             group_id=group_id).pack()
                )
        self.view_submissions = InlineKeyboardButton(
                text=self.actions.view_submissions_text,
                callback_data=CallbackManage(user=user,
                                             action=self.
                                             actions.view_submissions_id,
                                             msg_id=msg_id,
                                             group_id=group_id).pack()
                )
        self.back = InlineKeyboardButton(
                text=self.actions.back_text,
                callback_data=CallbackManage(user=user,
                                             action=self.
                                             actions.back,
                                             msg_id=msg_id,
                                             group_id=group_id).pack()
                )


class AdminKeyboard:

    def __init__(self, user_id: str, msg_id: str, group_id: str) -> None:
        self.buttons = AdminKeyboardButtons(user_id, msg_id, group_id)
        self.keyboard_no_vote = InlineKeyboardMarkup(
                inline_keyboard=[[self.buttons.finish_contest],
                                 [self.buttons.view_votes],
                                 [self.buttons.view_submissions],
                                 [self.buttons.back]]
                )
        self.keyboard_vote_in_progress = InlineKeyboardMarkup(
                inline_keyboard=[[self.buttons.finish_vote],
                                 [self.buttons.view_votes],
                                 [self.buttons.view_submissions],
                                 [self.buttons.back]]
                )
        self.keyboard_back = InlineKeyboardMarkup(
                inline_keyboard=[[self.buttons.back],]
                )

    @classmethod
    def fromcallback(cls, cb: CallbackManage):
        return cls(cb.user, cb.msg_id, cb.group_id)
