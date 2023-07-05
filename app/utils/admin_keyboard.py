from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


class CallbackManage(CallbackData, prefix="adm"):
    action: str
    group_id: str


class AdminActions:
    chosen_group = "cg"
    start_contest_text = "Создать челлендж 🗳"
    start_contest_id = "0"
    finish_contest_text = "Начать голосование 🗳"
    finish_contest_id = "1"
    sure_start_vote_text = "Да, хочу начать голосование"
    sure_start_vote_id = "11"
    finish_vote_text = "Завершить голосование 🗳"
    finish_vote_id = "2"
    sure_finish_vote_text = "Да, хочу завершить голосование"
    sure_finish_vote_id = "22"
    view_votes_text = "Посмотреть текущие голоса"
    view_votes_id = "3"
    view_submissions_text = "Посмотреть фотографии"
    view_submissions_id = "4"
    add_admin_text = "Добавить админа"
    add_admin_id = "5"
    delete_submission_text = "Удалить фотку"
    delete_submission_id = "6"
    delete_admin_text = "Удалить админа"
    delete_admin_id = "7"
    back = "b"
    back_text = "Назад"


class AdminKeyboardButtons:
    def __init__(self, group_id: str) -> None:
        self.actions = AdminActions()
        self.start_contest = InlineKeyboardButton(
            text=self.actions.start_contest_text,
            callback_data=CallbackManage(
                action=self.actions.start_contest_id, group_id=group_id
            ).pack(),
        )
        self.finish_contest = InlineKeyboardButton(
            text=self.actions.finish_contest_text,
            callback_data=CallbackManage(
                action=self.actions.finish_contest_id, group_id=group_id
            ).pack(),
        )
        self.sure_start_vote = InlineKeyboardButton(
            text=self.actions.sure_start_vote_text,
            callback_data=CallbackManage(
                action=self.actions.sure_start_vote_id, group_id=group_id
            ).pack(),
        )
        self.sure_finish_vote = InlineKeyboardButton(
            text=self.actions.sure_finish_vote_text,
            callback_data=CallbackManage(
                action=self.actions.sure_finish_vote_id, group_id=group_id
            ).pack(),
        )
        self.finish_vote = InlineKeyboardButton(
            text=self.actions.finish_vote_text,
            callback_data=CallbackManage(
                action=self.actions.finish_vote_id, group_id=group_id
            ).pack(),
        )
        self.view_votes = InlineKeyboardButton(
            text=self.actions.view_votes_text,
            callback_data=CallbackManage(
                action=self.actions.view_votes_id, group_id=group_id
            ).pack(),
        )
        self.view_submissions = InlineKeyboardButton(
            text=self.actions.view_submissions_text,
            callback_data=CallbackManage(
                action=self.actions.view_submissions_id, group_id=group_id
            ).pack(),
        )
        self.add_admin = InlineKeyboardButton(
            text=self.actions.add_admin_text,
            callback_data=CallbackManage(
                action=self.actions.add_admin_id, group_id=group_id
            ).pack(),
        )
        self.delete_submission = InlineKeyboardButton(
            text=self.actions.delete_submission_text,
            callback_data=CallbackManage(
                action=self.actions.delete_submission_id, group_id=group_id
            ).pack(),
        )
        self.delete_admin = InlineKeyboardButton(
            text=self.actions.delete_admin_text,
            callback_data=CallbackManage(
                action=self.actions.delete_admin_id, group_id=group_id
            ).pack(),
        )
        self.back = InlineKeyboardButton(
            text=self.actions.back_text,
            callback_data=CallbackManage(
                action=self.actions.back, group_id=group_id
            ).pack(),
        )


class AdminKeyboard:
    def __init__(self, group_id: str) -> None:
        self.buttons = AdminKeyboardButtons(group_id)
        self.keyboard_no_contest = InlineKeyboardMarkup(
            inline_keyboard=[
                [self.buttons.start_contest],
                [self.buttons.add_admin],
                [self.buttons.back],
            ]
        )
        self.keyboard_no_vote = InlineKeyboardMarkup(
            inline_keyboard=[
                [self.buttons.finish_contest],
                [self.buttons.view_submissions],
                [self.buttons.delete_submission],
                [self.buttons.add_admin],
                [self.buttons.back],
            ]
        )
        self.keyboard_vote_in_progress = InlineKeyboardMarkup(
            inline_keyboard=[
                [self.buttons.finish_vote],
                [self.buttons.view_votes],
                [self.buttons.add_admin],
                [self.buttons.back],
            ]
        )
        self.keyboard_no_contest_own = InlineKeyboardMarkup(
            inline_keyboard=[
                [self.buttons.start_contest],
                [self.buttons.add_admin],
                [self.buttons.delete_admin],
                [self.buttons.back],
            ]
        )
        self.keyboard_no_vote_own = InlineKeyboardMarkup(
            inline_keyboard=[
                [self.buttons.finish_contest],
                [self.buttons.view_submissions],
                [self.buttons.delete_submission],
                [self.buttons.add_admin],
                [self.buttons.delete_admin],
                [self.buttons.back],
            ]
        )
        self.keyboard_vote_in_progress_own = InlineKeyboardMarkup(
            inline_keyboard=[
                [self.buttons.finish_vote],
                [self.buttons.view_votes],
                [self.buttons.add_admin],
                [self.buttons.delete_admin],
                [self.buttons.back],
            ]
        )
        self.keyboard_are_you_sure = InlineKeyboardMarkup(
            inline_keyboard=[
                [self.buttons.sure_finish_vote],
                [self.buttons.back],
            ]
        )
        self.keyboard_are_you_sure_start = InlineKeyboardMarkup(
            inline_keyboard=[
                [self.buttons.sure_start_vote],
                [self.buttons.back],
            ]
        )
        self.keyboard_back = InlineKeyboardMarkup(
            inline_keyboard=[
                [self.buttons.back],
            ]
        )

    @classmethod
    def fromcallback(cls, cb: CallbackManage):
        return cls(cb.group_id)
