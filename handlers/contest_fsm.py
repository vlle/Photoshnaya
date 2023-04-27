from datetime import datetime
from babel.dates import format_date
from babel.dates import get_day_names, get_month_names
from typing import Any
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram import types
from aiogram import Bot
from utils.admin_keyboard import AdminKeyboard, CallbackManage
from db.db_operations import AdminDB
from handlers.internal_logic.admin import i_set_theme

class ContestCreate(StatesGroup):
    name_contest = State()
    are_you_sure = State()
    thanks_for_info = State()

async def set_theme(query: types.CallbackQuery, 
                    callback_data: CallbackManage, 
                    state: FSMContext,
                    msg: dict):
    if not query.message:
        return
    keyboard = AdminKeyboard.fromcallback(callback_data)
    await query.message.edit_text(text=msg["contest"]["create_greet_contest"])
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
    theme = message.text.split()
    string: dict[str, Any] = await state.get_data()
    keyboard = string["keyboard"]
    
    if (len(theme) > 1 or theme[0].lower() == 'отмена' 
            or theme[0].lower() == 'cancel'):
        text = msg["contest"]["cancel_contest"]
    else:
        text = await i_set_theme(theme[0], admin_unit, int(
            string["group"]))

        num = 1

        # Get the current date
        now = datetime.now()
        
        week_parent: dict[int, str] = {
                    0: 'понедельника',
                    1: 'вторника',
                    2: 'среды',
                    3: 'четверга',
                    4: 'субботы',
                    5: 'пятницы',
                    6: 'воскресенья'
                }
        #Get the short and full month names in Russian
        short_month_names = get_month_names('abbreviated', locale='ru')
        full_month_names = get_month_names('wide', locale='ru')

        # Get the day name and format the date
        day_names = get_day_names('wide', locale='ru')
        week = week_parent[now.weekday()]
        date_str = format_date(now.date(), format='d', locale='ru') + ' '  # day number
        date_str += full_month_names[now.month] + ' '  # month name
        date_now = date_str
        ret_text = msg["contest"]["start_contest"].format(num=num,
                                                          theme='#'+theme[0],
                                                          date_now=date_now,
                                                          date_str=date_str,
                                                          week=week)
        message_to_pin = await bot.send_message(chat_id=string["group"],
                                                text=ret_text)
        is_messaged_pinned = await bot.pin_chat_message(chat_id=string["group"],
                                                        message_id=message_to_pin.message_id)
        if not is_messaged_pinned:
            await bot.send_message(chat_id=string["group"],
                                   text=msg["contest"]["err"])
    await state.clear()
    await bot.edit_message_text(text=text,
                                chat_id=string["user_id"],
                                message_id=string["msg_id"],
                                reply_markup=keyboard.keyboard_back)



