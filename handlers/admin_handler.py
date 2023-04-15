from aiogram import types
from aiogram import Bot
from sqlalchemy import Engine
from db.db_operations import set_contest_theme, check_admin, build_theme, build_group, build_theme, get_contest_theme, register_group, register_admin, build_user

async def set_theme(message: types.Message, bot: Bot, engine: Engine):
    if not message.text or not message.from_user:
        return
    user_theme = message.text.split()
    user_id = message.from_user.id
    group_id = message.chat.id
    admin_right = check_admin(engine, user_id, group_id)
    if admin_right is False:
        #delete?
        #msg = "Нельзя, ты не админ."
        #await bot.send_message(message.chat.id, msg)
        return
    theme = build_theme(user_theme)
    if (len(user_theme) == 1):
        msg = 'Забыл название темы, админ\nПример: /set_theme #пляжи'
        await bot.send_message(message.chat.id, msg)
        return msg

    time = 604800
    msg = set_contest_theme(engine, user_id, group_id, theme, time) + " = новая тема"
    await bot.send_message(message.chat.id, msg)

async def get_theme(message: types.Message, bot: Bot, engine: Engine):
    if not message.chat or not message.chat.id:
        return

    chat_id = message.chat.id
    theme = get_contest_theme(engine, chat_id)
    msg = f"Текущая тема: {theme}"
    await bot.send_message(message.chat.id, msg)


async def on_user_join(message: types.Message, bot: Bot, engine: Engine):
    msg = "Добавили в чат, здоров!"
    group = build_group(message.chat.full_name, message.chat.id, "none")
    reg_msg = register_group(engine, group)
    if (reg_msg == "Группа уже зарегистрирована. 😮"):
        await bot.send_message(message.chat.id, msg)
        await bot.send_message(message.chat.id, reg_msg)
        return

    if (message.from_user and message.from_user.username):
        adm_user = build_user(message.from_user.username,
                              message.from_user.full_name,
                              message.from_user.id)
        register_admin(engine, adm_user, str(message.chat.id))
        msg = f"Добавил в качестве админа {message.from_user.username}"
    if (message.chat and message.chat.id):
        await bot.send_message(message.chat.id, msg)
        await bot.send_message(message.chat.id, reg_msg)




