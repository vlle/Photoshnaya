from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters.callback_data import CallbackData

class CallbackVote(CallbackData, prefix="vote"):
    user: str
    action: str
    current_photo_count: str
    current_photo_id: str
    amount_photos: str
    group_id: str

class Actions():
    next = "➡️"
    prev = "⬅️"
    no_like = '🤍'
    like = '❤️'
    amount = '/'
    count = '-'

class KeyboardButtons():
    def __init__(self, user, group_id, current_photo_id, current_photo_count, amount_photos) -> None:
        self.actions = Actions()
        self.callback_data = CallbackVote(user=user,
                                          action="none",
                                          current_photo_id=current_photo_id,
                                          current_photo_count=current_photo_count,
                                          amount_photos=amount_photos,
                                          group_id=group_id)
        self.button_next = InlineKeyboardButton(
                text=self.actions.next,
                callback_data=CallbackVote(user=user,
                                           action=self.
                                           actions.next,
                                           current_photo_id=current_photo_id,
                                           current_photo_count=current_photo_count,
                                           amount_photos=amount_photos,
                                           group_id=group_id).pack()
                )
        self.button_prev = InlineKeyboardButton(
                text=self.actions.prev,
                callback_data=CallbackVote(user=user,
                                           action=self.
                                           actions.prev,
                                           current_photo_id=current_photo_id,
                                           current_photo_count=current_photo_count,
                                           amount_photos=amount_photos,
                                           group_id=group_id).pack()
                )
        self.no_like = InlineKeyboardButton(
                text=self.actions.no_like,
                callback_data=CallbackVote(user=user,
                                           action=self.
                                           actions.no_like,
                                           current_photo_id=current_photo_id,
                                           current_photo_count=current_photo_count,
                                           amount_photos=amount_photos,
                                           group_id=group_id).pack()
                )
        self.like = InlineKeyboardButton(
                text=self.actions.like,
                callback_data=CallbackVote(user=user,
                                           action=self.
                                           actions.like,
                                           current_photo_id=current_photo_id,
                                           current_photo_count=current_photo_count,
                                           amount_photos=amount_photos,
                                           group_id='').pack()
                )
        self.amount = InlineKeyboardButton(
                text=current_photo_count+self.actions.amount+amount_photos,
                callback_data=CallbackVote(user=user,
                                           action=self.
                                           actions.count,
                                           current_photo_id=current_photo_id,
                                           current_photo_count=current_photo_count,
                                           amount_photos=amount_photos,
                                           group_id=group_id).pack()
                )


class Keyboard():
    def __init__(self, user: str, current_photo_id: str, current_photo_count: str, amount_photos: str, group_id: str) -> None:
        self.buttons = KeyboardButtons(user, group_id, current_photo_id, current_photo_count, amount_photos)
        self.keyboard_vote = InlineKeyboardMarkup(
                inline_keyboard=[
                    [self.buttons.button_prev,
                     self.buttons.amount,
                     self.buttons.button_next],
                    [self.buttons.no_like]
                    ]
                )
        self.keyboard_liked_vote = InlineKeyboardMarkup(
                inline_keyboard=[
                    [self.buttons.button_prev,
                     self.buttons.amount,
                     self.buttons.button_next],
                    [self.buttons.like]
                    ]
                )
