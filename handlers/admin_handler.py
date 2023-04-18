from asyncio import sleep as async_sleep
from aiogram import types
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.utils.keyboard import InlineKeyboardBuilder
from magic_filter.operations import call
from db.db_classes import Group
from utils.TelegramUserClass import TelegramDeserialize
from handlers.internal_logic.admin import i_set_theme
from handlers.internal_logic.on_join import i_on_user_join
from db.db_operations import RegisterDB, AdminDB
from utils.admin_keyboard import AdminKeyboard, CallbackManage, AdminActions




async def callback_back(query: types.CallbackQuery, bot: Bot, callback_data: CallbackManage, admin_unit: AdminDB):
    admin_right = admin_unit.select_all_administrated_groups(int(callback_data.user))

    if not query.message:
        return
    if len(admin_right) == 0:
        msg = 'Ты не являешься администратором.\nЧтобы стать администратором в группе -- добавь меня с правами админа в чат.'
        await bot.send_message(int(callback_data.user), msg)
        return

    builder = InlineKeyboardBuilder()
    data = callback_data
    data.action = AdminActions.chosen_group
    data.group_id = '-1'


    for admin in admin_right:
        data.group_id = admin[1]
        builder.button(text=f"{admin[0]}", callback_data=data.pack())

    builder.adjust(1, 1)

    msg = 'Выберите группу'
    await bot.edit_message_text(text=msg, chat_id=callback_data.user, message_id=query.message.message_id, reply_markup=builder.as_markup())


async def cmd_choose_group(message: types.Message, bot: Bot, admin_unit: AdminDB):
    if not message.text:
        return
    user, _ = TelegramDeserialize.unpack(message)
    admin_right = admin_unit.select_all_administrated_groups(user.telegram_id)

    if len(admin_right) == 0:
        msg = 'Ты не являешься администратором.\nЧтобы стать администратором в группе -- добавь меня с правами админа в чат.'
        await bot.send_message(user.telegram_id, msg)
        return

    builder = InlineKeyboardBuilder()
    data = CallbackManage(user=str(user.telegram_id),
                         action=AdminActions.chosen_group,
                         msg_id=str(user.message_id),
                         group_id='-1')


    for admin in admin_right:
        data.group_id = admin[1]
        builder.button(text=f"{admin[0]}", callback_data=data.pack())

    builder.adjust(1, 1)

    msg = 'Выберите группу'
    await bot.send_message(user.telegram_id, msg, reply_markup=builder.as_markup())


async def cmd_action_choose(query: types.CallbackQuery, bot: Bot, callback_data: CallbackManage, admin_unit: AdminDB):

    if not query.message:
        return
    msg = 'Выберите ваше действие'
    print(callback_data)
    keyboard = AdminKeyboard.fromcallback(callback_data)
    if 'vote' == 'vote':
        await bot.edit_message_text(text=msg, chat_id=callback_data.user, message_id=query.message.message_id, reply_markup=keyboard.keyboard_no_vote)
    else:
        await bot.edit_message_text(text=msg, chat_id=callback_data.user, message_id=query.message.message_id, reply_markup=keyboard.keyboard_vote_in_progress)



async def cmd_finish_contest(query: types.CallbackQuery, bot: Bot, callback_data: CallbackManage, admin_unit: AdminDB):
    pass

    #except TelegramBadRequest:
    #    if data.group_id == '-1':
    #        await bot.edit_message_text(text=msg, chat_id=callback_data.user, message_id=query.message.message_id)
    #        print(1)
    #    else:
    #        keyboard = AdminKeyboard(callback_data.user, callback_data.msg_id, callback_data.group_id)
    #        if data.action == AdminActions.finish_contest_id:
    #            # start vote availability
    #                # TODO: add contest generation link
    #            # show top 3 res 
    #            # show all res
    #            msg = f'Ссылка для голосования: https://t.me/Photoshnaya_bot?start={data.group_id}'
    #            await bot.edit_message_text(text=msg, chat_id=callback_data.user, message_id=query.message.message_id, reply_markup=keyboard.keyboard_back)
    #        elif data.action == AdminActions.view_votes_id:
    #            # show all res
    #            await bot.send_message(text='view_votes_id', chat_id=callback_data.user)
    #        elif data.action == AdminActions.view_submissions_id:
    #            # show all photo as media group
    #            await bot.send_message(text='view_submissions_id', chat_id=callback_data.user)
    #        elif data.action == AdminActions.back:
    #            await bot.edit_message_text(text=msg, chat_id=callback_data.user, message_id=query.message.message_id, reply_markup=keyboard.keyboard_back)


async def view_votes(query: types.CallbackQuery, bot: Bot, callback_data: CallbackManage, admin_unit: AdminDB):
    pass

async def view_submissions(query: types.CallbackQuery, bot: Bot, callback_data: CallbackManage, admin_unit: AdminDB):
    pass


async def finish_contest(query: types.CallbackQuery, bot: Bot, callback_data: CallbackManage, admin_unit: AdminDB):
    pass



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
