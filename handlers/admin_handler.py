from asyncio import sleep as async_sleep
from aiogram import types
from aiogram import Bot
from utils.TelegramUserClass import TelegramDeserialize
from handlers.internal_logic.admin import i_set_theme
from handlers.internal_logic.on_join import i_on_user_join
from db.db_operations import RegisterDB, AdminDB
from utils.admin_keyboard import AdminKeyboard


async def cmd_admin_start(message: types.Message, bot: Bot, admin_unit: AdminDB):
    if not message.text:
        return
    user, _ = TelegramDeserialize.unpack(message)
    admin_right = admin_unit.select_all_administrated_groups(user.telegram_id)
    if len(admin_right) == 0:
        msg = 'Ты не являешься администратором для меня.'
        await bot.send_message(message.chat.id, msg)
        return

    msg = 'Выберите ваше действие'
    keyboard = AdminKeyboard(str(user.telegram_id), admin_right[0])
    await bot.send_message(message.chat.id, msg, reply_markup=keyboard.keyboard_start)


async def cmd_help(message: types.Message, bot: Bot, admin_unit: AdminDB):
    if not message.text or not message.from_user:
        return
    if message.chat.type != 'private':
        return
    group_id = message.text.split(' ')[1]
    user, _ = TelegramDeserialize.unpack(message)
    admin_right = admin_unit.check_admin(user.telegram_id, int(group_id))
    if admin_right is False:
        return
    msg = '1. /set_theme + название темы в групповом чате\n2. /get_all_photos + айди группы'
    await bot.send_message(message.chat.id, msg)


async def set_theme(message: types.Message, bot: Bot, admin_unit: AdminDB):
    if not message.text or not message.from_user:
        return
    user, chat = TelegramDeserialize.unpack(message)
    print(user)
    print(chat)
    admin_right = admin_unit.check_admin(user.telegram_id, chat.telegram_id)
    if admin_right is False:
        return

    user_theme = message.text.split()
    msg = i_set_theme(user_theme, admin_unit, chat)
    await bot.send_message(message.chat.id, msg)


async def get_theme(message: types.Message, bot: Bot, admin_unit: AdminDB):
    if not message.text or not message.from_user:
        return
    user, chat = TelegramDeserialize.unpack(message)
    admin_right = admin_unit.check_admin(user.telegram_id, chat.telegram_id)
    if admin_right is False:
        return

    theme = admin_unit.get_contest_theme(chat.telegram_id)
    msg = f"Текущая тема: {theme}"
    await bot.send_message(message.chat.id, msg)

async def get_all_photos(message: types.Message, bot: Bot, admin_unit: AdminDB):
    if not message.text or not message.from_user:
        return
    if message.chat.type != 'private':
        return
    group_id = message.text.split(' ')[1]
    user, _ = TelegramDeserialize.unpack(message)
    admin_right = admin_unit.check_admin(user.telegram_id, int(group_id))
    if admin_right is False:
        return

    ids = admin_unit.select_contest_photos_ids(int(group_id))
    for id in ids:
        await bot.send_photo(chat_id=message.chat.id, photo=id)
        await async_sleep(0.5)

async def on_user_join(message: types.Message, bot: Bot, register_unit: RegisterDB):
    user, chat = TelegramDeserialize.unpack(message, message_id_not_exists=True)

    msg, reg_msg = i_on_user_join(register_unit=register_unit, user=user, chat=chat)

    await bot.send_message(chat.telegram_id, msg)
    if reg_msg:
        await bot.send_message(chat.telegram_id, reg_msg)
