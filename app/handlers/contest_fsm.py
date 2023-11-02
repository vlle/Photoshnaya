from datetime import datetime, timedelta
from typing import Any

from aiogram import Bot, types
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from babel.dates import format_date, get_month_names

from db.db_operations import AdminDB, ObjectFactory
from handlers.internal_logic.admin import i_set_theme
from reminders import add_reminder
from utils.admin_keyboard import AdminKeyboard, CallbackManage


class ContestCreate(StatesGroup):
    name_contest = State()
    are_you_sure = State()
    will_you_post = State()
    thanks_for_info = State()


async def set_theme(
    query: types.CallbackQuery,
    callback_data: CallbackManage,
    state: FSMContext,
    msg: dict,
):
    if not query.message:
        return
    keyboard: AdminKeyboard = AdminKeyboard.fromcallback(callback_data)
    await query.message.edit_text(
        text=msg["contest"]["create_greet_contest"], parse_mode="HTML"
    )
    data = {}
    data["group"] = callback_data.group_id
    data["user_id"] = query.from_user.id
    data["msg_id"] = query.message.message_id
    data["keyboard"] = keyboard
    data["file_id"] = None
    await state.set_data(data)
    await state.set_state(ContestCreate.name_contest)


async def set_theme_accept_message(
    message: types.Message, bot: Bot, state: FSMContext, admin_unit: AdminDB, msg: dict
):
    if not message.text:
        return
    data_theme_date = message.text.split()
    data: dict[str, Any] = await state.get_data()

    if (
        len(data_theme_date) != 1
        or data_theme_date[0].lower() == "отмена"
        or data_theme_date[0].lower() == "cancel"
    ):
        text = msg["contest"]["cancel_contest"]
        keyboard: AdminKeyboard = data["keyboard"]
        await state.clear()
        await bot.edit_message_text(
            text=text,
            chat_id=data["user_id"],
            message_id=data["msg_id"],
            reply_markup=keyboard.keyboard_back,
        )
    else:
        # temporary turn-off time = data_theme_date[1] + data_theme_date[2]
        # time = "1неделя"
        time = "2неделя"
        theme = ObjectFactory.build_theme_fsm(data_theme_date[0])
        week_to_second: dict[str, int] = {
            "1неделя": 604800,
            "1неделю": 604800,
            "2недели": 1209600,
            "2неделя": 1209600,
            "3неделя": 1814400,
            "3недели": 1814400,
        }
        try:
            date_without_hms = datetime.utcnow().replace(
                hour=6, minute=0, second=0, microsecond=0
            )
            one_day = timedelta(days=1).total_seconds()
            time = int(week_to_second[time] + date_without_hms.timestamp() - one_day)
            try:
                await add_reminder(time, data["group"])
            except Exception as e:
                await message.reply("Не удалось установить напоминание")
                print(e)
        except KeyError:
            await message.reply(msg["admin"]["wrong_time"])
            await state.clear()
            return

        link = await admin_unit.get_last_results_link(int(data["group"]))
        if link is not None:
            link_msg = f'Результаты предыдущего челленджа вот <a href="{link}">тут</a>.'
        else:
            link_msg = ""
        text = await i_set_theme(theme, admin_unit, int(data["group"]), time)

        num = str(await admin_unit.count_contests(int(data["group"])))

        # Get the current date
        now = datetime.now()
        end = datetime.utcfromtimestamp(time)

        week_parent: dict[int, str] = {
            0: "понедельника",
            1: "вторника",
            2: "среды",
            3: "четверга",
            4: "пятницы",
            5: "субботы",
            6: "воскресенья",
        }

        # Get the short and full month names in Russian
        full_month_names = get_month_names("wide", locale="ru")

        # Get the day name and format the date
        week = week_parent[end.weekday()]
        date_now = format_date(now.date(), format="d", locale="ru") + " "  # day number
        date_now += full_month_names[now.month]  # month name
        date_str = format_date(end.date(), format="d", locale="ru") + " "
        date_str += full_month_names[end.month]

        ret_text = (
            msg["contest"]["start_contest"].format(
                num=num, theme=theme, date_now=date_now, date_str=date_str, week=week
            )
            + link_msg
        )
        await bot.edit_message_text(
            text=msg["contest"]["will_you_post"],
            chat_id=data["user_id"],
            message_id=data["msg_id"],
            parse_mode="HTML",
        )
        data["send"] = await bot.send_message(
            text=ret_text, chat_id=data["user_id"], parse_mode="HTML"
        )

        await state.set_data(data)
        await state.set_state(ContestCreate.will_you_post)


async def should_i_post_theme(
    message: types.Message, bot: Bot, state: FSMContext, msg: dict
):
    data: dict[str, Any] = await state.get_data()

    if message.text and (message.text.lower() == "ок" or message.text.lower() == "ok"):
        message_to_pin = await bot.copy_message(
            chat_id=data["group"],
            from_chat_id=data["user_id"],
            message_id=data["send"].message_id,
        )

        try:
            await bot.pin_chat_message(
                chat_id=data["group"], message_id=message_to_pin.message_id
            )
        except TelegramBadRequest:
            await bot.send_message(chat_id=data["group"], text=msg["contest"]["err"])
        await state.clear()
        return
    else:
        data["send"] = await message.copy_to(chat_id=data["user_id"], parse_mode="HTML")

        await state.set_data(data)
        await state.set_state(ContestCreate.will_you_post)
