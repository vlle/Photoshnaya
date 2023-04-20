from asyncio import sleep as async_sleep
from aiogram import types
from aiogram import Bot
from aiogram.types import CallbackQuery, InputMediaDocument, InputMediaPhoto, document
from aiogram.exceptions import TelegramBadRequest
from aiogram.utils.keyboard import InlineKeyboardBuilder
from magic_filter.operations import call
from sqlalchemy.util.langhelpers import counter
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
    vote_in_progress = admin_unit.get_current_vote_status(int(callback_data.group_id))
    if not vote_in_progress:
        await bot.edit_message_text(text=msg, chat_id=callback_data.user, message_id=query.message.message_id, reply_markup=keyboard.keyboard_no_vote)
    else:
        await bot.edit_message_text(text=msg, chat_id=callback_data.user, message_id=query.message.message_id, reply_markup=keyboard.keyboard_vote_in_progress)



async def cmd_finish_contest(query: types.CallbackQuery, bot: Bot, callback_data: CallbackManage, admin_unit: AdminDB):
    if not query.message:
        return
    admin_unit.change_current_vote_status(int(callback_data.group_id))
    keyboard = AdminKeyboard.fromcallback(callback_data)
    bot_link: str = "t.me/Photoshnaya_bot?start=" + callback_data.group_id + "_3"
    msg = f"Голосование запущено. Вот ссылка, отправьте ее в чат: {bot_link}"
    await bot.edit_message_text(text=msg, chat_id=callback_data.user, message_id=query.message.message_id, reply_markup=keyboard.keyboard_back)


async def cmd_finish_vote(query: types.CallbackQuery, bot: Bot, callback_data: CallbackManage, admin_unit: AdminDB):
    if not query.message:
        return
    admin_unit.change_current_vote_status(int(callback_data.group_id))
    keyboard = AdminKeyboard.fromcallback(callback_data)
    msg = 'Голосование завершено. Результаты:\n, отправьте их в чат'
    await bot.edit_message_text(text=msg, chat_id=callback_data.user, message_id=query.message.message_id, reply_markup=keyboard.keyboard_back)



async def view_votes(query: types.CallbackQuery, bot: Bot, callback_data: CallbackManage, admin_unit: AdminDB):
    pass

async def view_submissions(query: types.CallbackQuery, bot: Bot, callback_data: CallbackManage, admin_unit: AdminDB):
    cb = callback_data

    ids = admin_unit.select_contest_photos_ids_and_types(int(cb.group_id))
    if len(ids) == 0:
        return
    if len(ids) == 1:
        if ids[0][1] == 'photo':
            obj = InputMediaPhoto(type='photo', media=ids[0][0])
            await bot.send_photo(chat_id=query.from_user.id, photo=ids[0][0])
        else:
            await bot.send_document(chat_id=query.from_user.id, document=ids[0][0])

    submissions_photos = []
    submissions_docs = []
    for id in ids:
        if id[1] == 'photo':
            await send_other_type(submissions_docs, bot, query)
            obj = InputMediaPhoto(type='photo', media=id[0])
            submissions_photos.append(obj)
        else:
            await send_other_type(submissions_photos, bot, query)
            obj = InputMediaDocument(type='document', media=id[0])
            submissions_docs.append(obj)

        if len(submissions_photos) == 10 or len(submissions_docs) == 10:
            if len(submissions_docs) == 10:
                await bot.send_media_group(chat_id=query.from_user.id, media=submissions_docs)
                submissions_docs.clear()
            else:
                await bot.send_media_group(chat_id=query.from_user.id, media=submissions_photos)
                submissions_photos.clear()

    if len(submissions_photos) > 0 or len(submissions_docs) > 0:
        if len(submissions_photos) > 1:
            await bot.send_media_group(chat_id=query.from_user.id, media=submissions_photos)
        elif len(submissions_photos) == 1:
            await bot.send_photo(chat_id=query.from_user.id, photo=submissions_photos[0])
        if len(submissions_docs) > 1:
            await bot.send_media_group(chat_id=query.from_user.id, media=submissions_docs)
        elif len(submissions_docs) == 1:
            await bot.send_document(chat_id=query.from_user.id, document=submissions_docs[0].media)

    del submissions_photos
    del submissions_docs


async def send_other_type(list_of_object: list[InputMediaDocument | InputMediaPhoto], bot: Bot, query: CallbackQuery):
    if len(list_of_object) == 0:
        return
    if len(list_of_object) > 1:
        await bot.send_media_group(chat_id=query.from_user.id, media=list_of_object)
    elif len(list_of_object) == 1 and isinstance(list_of_object[0], InputMediaDocument):
        await bot.send_document(chat_id=query.from_user.id, document=list_of_object[0].media)
    elif len(list_of_object) == 1 and isinstance(list_of_object[0], InputMediaPhoto):
        await bot.send_photo(chat_id=query.from_user.id, photo=list_of_object[0].media)
    list_of_object.clear()
    await async_sleep(0.5)

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
        if admin_unit.select_file_type_by_file_id(id) == 'photo':
            await bot.send_photo(chat_id=message.chat.id, photo=id)
        else:
            await bot.send_document(chat_id=message.chat.id, document=id)
        await async_sleep(0.5)

async def on_user_join(message: types.Message, bot: Bot, register_unit: RegisterDB):
    user, chat = TelegramDeserialize.unpack(message, message_id_not_exists=True)

    msg, reg_msg = i_on_user_join(register_unit=register_unit, user=user, chat=chat)

    await bot.send_message(chat.telegram_id, msg)
    if reg_msg:
        await bot.send_message(chat.telegram_id, reg_msg)
