from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters.callback_data import CallbackData


class CallbackVote(CallbackData, prefix="vt"):
    action: str
    current_photo_count: str
    current_photo_id: str
    amount_photos: str
    group_id: str


class Actions:
    next = "➡️"
    next_text = "n"
    prev = "⬅️"
    prev_text = "pr"
    no_like = "🤍"
    no_like_text = "nl"
    like = "❤️"
    like_text = "l"
    amount = "/"
    count = "-"
    finish = "Отправить голос 🏁"
    finish_text = "f"


class KeyboardButtons:
    def __init__(
        self,
        group_id: str,
        current_photo_id: str,
        c_photo_count: str,
        amount_photos: str,
    ) -> None:
        self.actions = Actions()
        self.button_next = InlineKeyboardButton(
            text=self.actions.next,
            callback_data=CallbackVote(
                action=self.actions.next_text,
                current_photo_id=current_photo_id,
                current_photo_count=c_photo_count,
                amount_photos=amount_photos,
                group_id=group_id,
            ).pack(),
        )
        self.button_prev = InlineKeyboardButton(
            text=self.actions.prev,
            callback_data=CallbackVote(
                action=self.actions.prev_text,
                current_photo_id=current_photo_id,
                current_photo_count=c_photo_count,
                amount_photos=amount_photos,
                group_id=group_id,
            ).pack(),
        )
        self.no_like = InlineKeyboardButton(
            text=self.actions.no_like,
            callback_data=CallbackVote(
                action=self.actions.no_like_text,
                current_photo_id=current_photo_id,
                current_photo_count=c_photo_count,
                amount_photos=amount_photos,
                group_id=group_id,
            ).pack(),
        )
        self.like = InlineKeyboardButton(
            text=self.actions.like,
            callback_data=CallbackVote(
                action=self.actions.like_text,
                current_photo_id=current_photo_id,
                current_photo_count=c_photo_count,
                amount_photos=amount_photos,
                group_id=group_id,
            ).pack(),
        )
        self.amount = InlineKeyboardButton(
            text=c_photo_count + self.actions.amount + amount_photos,
            callback_data=CallbackVote(
                action=self.actions.count,
                current_photo_id=current_photo_id,
                current_photo_count=c_photo_count,
                amount_photos=amount_photos,
                group_id=group_id,
            ).pack(),
        )
        self.finish = InlineKeyboardButton(
            text=self.actions.finish,
            callback_data=CallbackVote(
                action=self.actions.finish_text,
                current_photo_id=current_photo_id,
                current_photo_count=c_photo_count,
                amount_photos=amount_photos,
                group_id=group_id,
            ).pack(),
        )


class Keyboard:
    def __init__(
        self,
        current_photo_id: str,
        current_photo_count: str,
        amount_photos: str,
        group_id: str,
    ) -> None:
        self.buttons = KeyboardButtons(
            group_id, current_photo_id, current_photo_count, amount_photos
        )
        self.keyboard_start = InlineKeyboardMarkup(
            inline_keyboard=[
                [self.buttons.amount, self.buttons.button_next],
                [self.buttons.no_like],
            ]
        )
        self.keyboard_start_liked = InlineKeyboardMarkup(
            inline_keyboard=[
                [self.buttons.amount, self.buttons.button_next],
                [self.buttons.like],
            ]
        )
        self.keyboard_vote = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    self.buttons.button_prev,
                    self.buttons.amount,
                    self.buttons.button_next,
                ],
                [self.buttons.no_like],
            ]
        )
        self.keyboard_vote_liked = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    self.buttons.button_prev,
                    self.buttons.amount,
                    self.buttons.button_next,
                ],
                [self.buttons.like],
            ]
        )
        self.keyboard_end = InlineKeyboardMarkup(
            inline_keyboard=[
                [self.buttons.button_prev, self.buttons.amount],
                [self.buttons.no_like],
                [self.buttons.finish],
            ]
        )
        self.keyboard_end_liked = InlineKeyboardMarkup(
            inline_keyboard=[
                [self.buttons.button_prev, self.buttons.amount],
                [self.buttons.like],
                [self.buttons.finish],
            ]
        )

    @classmethod
    def fromcallback(cls, cb: CallbackVote):
        return cls(
            group_id=cb.group_id,
            current_photo_count=cb.current_photo_count,
            current_photo_id=cb.current_photo_id,
            amount_photos=cb.amount_photos,
        )
