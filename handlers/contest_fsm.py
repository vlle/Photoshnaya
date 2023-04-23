import logging
from typing import Any, Dict

from aiogram import Bot, Dispatcher, F, Router, html
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)



class ContestCreate(StatesGroup):
    name_contest = State()
    are_you_sure = State()
    thanks_for_info = State()
    name = State()
    like_bots = State()
    language = State()


async def command_start(message: Message, state: FSMContext) -> None:
    await state.set_state(ContestCreate.name)
    await message.answer(
        "Hi there! What's your name?",
        reply_markup=ReplyKeyboardRemove
        (remove_keyboard=True),
    )


async def cancel_handler(message: Message, state: FSMContext) -> None:
    """
    Allow user to cancel any action
    """
    current_state = await state.get_state()
    if current_state is None:
        return

    logging.info("Cancelling state %r", current_state)
    await state.clear()
    await message.answer(
        "Cancelled.",
        reply_markup=ReplyKeyboardRemove
        (remove_keyboard=True),
    )


async def process_name(message: Message, state: FSMContext) -> None:
    if not message.text:
        return
    await state.update_data(name=message.text)
    await state.set_state(ContestCreate.like_bots)
    await message.answer(
        f"Nice to meet you, {html.quote(message.text)}!\nDid you like to write bots?",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(text="Yes"),
                    KeyboardButton(text="No"),
                ]
            ],
            resize_keyboard=True,
        ),
    )


async def process_dont_like_write_bots(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await state.clear()
    await message.answer(
        "Not bad not terrible.\nSee you soon.",
        reply_markup=ReplyKeyboardRemove
        (remove_keyboard=True),
    )
    await show_summary(message=message, data=data, positive=False)


async def process_like_write_bots(message: Message, state: FSMContext) -> None:
    await state.set_state(ContestCreate.language)

    await message.reply(
        "Cool! I'm too!\nWhat programming language did you use for it?",
        reply_markup=ReplyKeyboardRemove
        (remove_keyboard=True),
    )


async def process_unknown_write_bots(message: Message, state: FSMContext) -> None:
    await message.reply("I don't understand you :(")


async def process_language(message: Message, state: FSMContext) -> None:
    data = await state.update_data(language=message.text)
    await state.clear()
    text = (
        "Thank for all! Python is in my hearth!\nSee you soon."
        if message.text.casefold() == "python"
        else "Thank for information!\nSee you soon."
    )
    await message.answer(text)
    await show_summary(message=message, data=data)


async def show_summary(message: Message, data: Dict[str, Any], positive: bool = True) -> None:
    name = data["name"]
    language = data.get("language", "<something unexpected>")
    text = f"I'll keep in mind that, {html.quote(name)}, "
    text += (
        f"you like to write bots with {html.quote(language)}."
        if positive
        else "you don't like to write bots, so sad..."
    )
    await message.answer(text=text,
        reply_markup=ReplyKeyboardRemove
        (remove_keyboard=True))


async def state_router():
    form_router = Router()
    form_router.message.register(command_start, Command(commands=["check"]))
    form_router.message.register(cancel_handler, Command("cancel"))
    form_router.message.register(cancel_handler, F.text.casefold() == "cancel")
    form_router.message.register(process_name, ContestCreate.name)
    form_router.message.register(process_dont_like_write_bots, ContestCreate.like_bots,
                                 F.text.casefold() == "no")
    form_router.message.register(process_like_write_bots, ContestCreate.like_bots,
                                 F.text.casefold() == "yes")
    form_router.message.register(process_unknown_write_bots, ContestCreate.like_bots)
    form_router.message.register(process_language, ContestCreate.language)

    return form_router
