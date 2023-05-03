from datetime import datetime, timedelta
from aiogram.exceptions import TelegramBadRequest
from aiogram.types.keyboard_button import KeyboardButton
from babel.dates import format_date
from babel.dates import get_month_names
from typing import Any, List
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram import types
from aiogram import Bot
from utils.admin_keyboard import AdminKeyboard, CallbackManage
from db.db_operations import AdminDB, ObjectFactory
from handlers.internal_logic.admin import i_set_theme

class ContestCreate(StatesGroup):
    name_contest = State()
    are_you_sure = State()
    will_you_post = State()
    thanks_for_info = State()

async def set_theme(query: types.CallbackQuery, 
                    callback_data: CallbackManage, 
                    state: FSMContext,
                    msg: dict):
    if not query.message:
        return
    keyboard: AdminKeyboard = AdminKeyboard.fromcallback(callback_data)
    await query.message.edit_text(text=msg["contest"]["create_greet_contest"],
                                  parse_mode="HTML")
    data = {}
    data["group"] = callback_data.group_id
    data["user_id"] = query.from_user.id
    data["msg_id"] = query.message.message_id
    data["keyboard"] = keyboard
    await state.set_data(data)
    await state.set_state(ContestCreate.name_contest)

async def set_theme_accept_message(message: types.Message, bot: Bot,
                                   state: FSMContext, admin_unit: AdminDB,
                                   msg: dict):
    if not message.text:
        return
    data_theme_date = message.text.split()
    data: dict[str, Any] = await state.get_data()
    
    if (len(data_theme_date) != 3 or data_theme_date[0].lower() == 'отмена' 
            or data_theme_date[0].lower() == 'cancel'):
        text = msg["contest"]["cancel_contest"]
        keyboard: AdminKeyboard = data["keyboard"]
        await state.clear()
        await bot.edit_message_text(text=text,
                                    chat_id=data["user_id"],
                                    message_id=data["msg_id"],
                                    reply_markup=keyboard.keyboard_back)
    else:
        time = data_theme_date[1] + data_theme_date[2]
        theme = ObjectFactory.build_theme_fsm(data_theme_date[0])
        week_to_second: dict[str, int] ={
                '1неделя': 604800,
                '1неделю': 604800,
                '2недели': 1209600,
                '2неделя': 1209600,
                '3неделя': 1814400,
                '3недели': 1814400,
                }
        try:
            time = week_to_second[time]
        except KeyError:
            await message.reply(msg["admin"]["wrong_time"])
            await state.clear()
            return

        link = await admin_unit.get_last_results_link(int(data["group"]))
        if link is not None:
            link_msg = f'Результаты предыдущего челленджа вот <a href="{link}">тут</a>.'
        else:
            link_msg = ''
        text = await i_set_theme(theme, admin_unit, int(
            data["group"]), time)


        num = str(await admin_unit.count_contests(int(data["group"])))

        # Get the current date
        now = datetime.now()
        end = timedelta(seconds=time) + now

        week_parent: dict[int, str] = {
                0: 'понедельника',
                1: 'вторника',
                2: 'среды',
                3: 'четверга',
                4: 'пятницы',
                5: 'субботы',
                6: 'воскресенья'
                }

        #Get the short and full month names in Russian
        full_month_names = get_month_names('wide', locale='ru')

        # Get the day name and format the date
        week = week_parent[end.weekday()]
        date_now = format_date(now.date(), format='d', locale='ru') + ' '  # day number
        date_now += full_month_names[now.month]  # month name
        date_str = format_date(end.date(), format='d', locale='ru') + ' '
        date_str += full_month_names[end.month]


        ret_text = msg["contest"]["start_contest"].format(num=num,
                                                          theme=theme,
                                                          date_now=date_now,
                                                          date_str=date_str,
                                                          week=week) + link_msg
        data["text"] = ret_text
        bots_text = msg["contest"]["will_you_post"] + ret_text
        await bot.edit_message_text(text=bots_text,
                                    chat_id=data["user_id"],
                                    message_id=data["msg_id"],
                                    parse_mode="HTML")
        await state.set_data(data)
        await state.set_state(ContestCreate.will_you_post)

async def should_i_post_theme(message: types.Message,
                              bot: Bot,
                              state: FSMContext,
                              msg: dict):
        data: dict[str, Any] = await state.get_data()
        ret_text = data["text"]
        if (message.text and
            (message.text.lower() == "ок" or message.text.lower() == "ok")):
            message_to_pin = await bot.send_message(chat_id=data["group"],
                                                    text=ret_text,
                                                    parse_mode="HTML")
            try:
                await bot.pin_chat_message(chat_id=data["group"],
                                                            message_id=message_to_pin.message_id)
            except TelegramBadRequest:
                await bot.send_message(chat_id=data["group"],
                                       text=msg["contest"]["err"])
            await state.clear()
        else:
            data["text"] = message.html_text
            await state.set_data(data)
            bots_text = msg["contest"]["will_you_post"] + message.html_text
            await bot.edit_message_text(text=bots_text,
                                        chat_id=data["user_id"],
                                        message_id=data["msg_id"],
                                        parse_mode="HTML")
            await state.set_state(ContestCreate.will_you_post)
