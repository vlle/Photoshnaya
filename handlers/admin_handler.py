from asyncio import sleep as async_sleep
from aiogram import types
from aiogram import Bot
from aiogram.types import InputMediaDocument, InputMediaPhoto
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession
from utils.TelegramUserClass import TelegramDeserialize
from handlers.internal_logic.admin import i_set_theme
from handlers.internal_logic.on_join import i_on_user_join
from db.db_operations import RegisterDB, AdminDB, VoteDB
from utils.admin_keyboard import AdminKeyboard, CallbackManage, AdminActions

async def cmd_choose_group(message: types.Message, bot: Bot,
                           admin_unit: AdminDB, msg: dict):
    if not message.text:
        return
    user, _ = TelegramDeserialize.unpack(message)
    admin_right = admin_unit.select_all_administrated_groups(user.telegram_id)

    if len(admin_right) == 0:
        await bot.send_message(user.telegram_id,
                               msg["admin"]["you_are_not_admin"])
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

    await bot.send_message(user.telegram_id, msg["admin"]["choose_group"],
                           reply_markup=builder.as_markup())



async def callback_back(query: types.CallbackQuery, bot: Bot,
                        callback_data: CallbackManage, admin_unit: AdminDB,
                        msg: dict):
    admin_right = admin_unit.select_all_administrated_groups(
            int(callback_data.user)
            )

    if not query.message:
        return
    if len(admin_right) == 0:
        await bot.send_message(int(callback_data.user),
                               msg["admin"]["you_are_not_admin"])
        return

    builder = InlineKeyboardBuilder()
    data = callback_data
    data.action = AdminActions.chosen_group
    data.group_id = '-1'

    for admin in admin_right:
        data.group_id = admin[1]
        builder.button(text=f"{admin[0]}", callback_data=data.pack())

    builder.adjust(1, 1)

    await bot.edit_message_text(text=msg["admin"]["choose_group"],
                                chat_id=callback_data.user,
                                message_id=query.message.message_id,
                                reply_markup=builder.as_markup())



async def cmd_action_choose(query: types.CallbackQuery, bot: Bot,
                            callback_data: CallbackManage,
                            admin_unit: AdminDB, msg: dict):

    if not query.message:
        return
    print(callback_data)
    keyboard = AdminKeyboard.fromcallback(callback_data)
    vote_in_progress = admin_unit.get_current_vote_status(
            int(callback_data.group_id)
            )

    if not vote_in_progress:
        keyboard_r = keyboard.keyboard_no_vote
    else:
        keyboard_r = keyboard.keyboard_vote_in_progress

    await bot.edit_message_text(text=msg["admin"]["choose_action"],
                                chat_id=callback_data.user,
                                message_id=query.message.message_id,
                                reply_markup=keyboard_r)


async def cmd_check_if_sure(query: types.CallbackQuery, bot: Bot,
                            callback_data: CallbackManage, msg: dict):
    if not query.message:
        return
    keyboard = AdminKeyboard.fromcallback(callback_data)
    await bot.edit_message_text(text=msg["admin"]["are_you_sure_F"],
                                chat_id=callback_data.user,
                                message_id=query.message.message_id,
                                reply_markup=keyboard.keyboard_are_you_sure)


async def cmd_check_if_sure_vote(query: types.CallbackQuery, bot: Bot,
                                 callback_data: CallbackManage, msg: dict):
    if not query.message:
        return
    keyboard = AdminKeyboard.fromcallback(callback_data)
    await bot.edit_message_text(text=msg["admin"]["are_you_sure_S"],
                                chat_id=callback_data.user,
                                message_id=query.message.message_id,
                                reply_markup=keyboard.keyboard_are_you_sure_start)


async def cmd_finish_contest(query: types.CallbackQuery, bot: Bot,
                             callback_data: CallbackManage,
                             admin_unit: AdminDB):
    if not query.message:
        return
    admin_unit.change_current_vote_status(int(callback_data.group_id))
    keyboard = AdminKeyboard.fromcallback(callback_data)
    bot_t = await bot.me()
    bot_link = f"t.me/{bot_t.username}?start=" + callback_data.group_id + "_3"
    msg = f"Голосование запущено. Вот ссылка, отправьте ее в чат: {bot_link}"
    msg_duplicate = f"На всякий случай дублирую отдельным сообщением: {bot_link}"
    await bot.send_message(text=msg_duplicate, chat_id=callback_data.user)
    await bot.edit_message_text(text=msg,
                                chat_id=callback_data.user,
                                message_id=query.message.message_id,
                                reply_markup=keyboard.keyboard_back)


async def cmd_finish_vote(query: types.CallbackQuery, bot: Bot,
                          callback_data: CallbackManage, admin_unit: AdminDB,
                          msg: dict):
    if not query.message:
        return
    admin_unit.change_current_vote_status(int(callback_data.group_id))
    keyboard = AdminKeyboard.fromcallback(callback_data)
    vote = VoteDB(admin_unit.engine)


    ids = admin_unit.select_contest_photos_ids_and_types(int(callback_data.group_id))
    if len(ids) == 0:
        return
    id, user = vote.select_winner_from_contest(int(callback_data.group_id))
    if not user:
        return

    file_id = vote.select_file_id(id)
    likes = vote.select_all_likes_file_id(int(callback_data.group_id), file_id)
    type_photo = vote.select_file_type_by_file_id(file_id)
    await bot.edit_message_text(text=msg["admin"]["vote_end"],
                                chat_id=callback_data.user,
                                message_id=query.message.message_id,
                                reply_markup=keyboard.keyboard_back)

    user_info = f"Победитель: @{user[0]}, {user[1]}\nЛайков: {likes}"
    if type_photo == 'photo':
        await bot.send_photo(chat_id=query.from_user.id, photo=file_id,
                             caption=user_info)
    else:
        await bot.send_document(chat_id=query.from_user.id, document=file_id,
                                caption=user_info)
    ids = admin_unit.select_contest_photos_ids_and_types(int(callback_data.group_id))
    if len(ids) == 0:
        return
    await internal_view_submissions(query.from_user.id, ids,
                                    bot, admin_unit, callback_data)
    vote.erase_all_photos(int(callback_data.group_id))



async def view_votes(query: types.CallbackQuery, bot: Bot,
                     callback_data: CallbackManage, admin_unit: AdminDB):

    pass


async def view_submissions(query: types.CallbackQuery, bot: Bot,
                           callback_data: CallbackManage, admin_unit: AdminDB):
    cb = callback_data

    ids = admin_unit.select_contest_photos_ids_and_types(int(cb.group_id))
    if len(ids) == 0:
        return
    await internal_view_submissions(query.from_user.id, ids, bot, admin_unit,
                                    callback_data)


async def internal_view_submissions(chat_id: int, ids: list, bot: Bot,
                                    admin_unit: AdminDB,
                                    callback_data: CallbackManage):
    cb = callback_data
    if len(ids) == 1:
        if ids[0][1] == 'photo':
            await bot.send_photo(chat_id=chat_id, photo=ids[0][0])
        else:
            await bot.send_document(chat_id=chat_id, document=ids[0][0])
        return

    MAX_SUBMISSIONS = 10
    submissions_photos = []
    submissions_docs = []
    vote = VoteDB(admin_unit.engine)
    for id in ids:
        media_type, media = id[1], id[0]
        if media_type == 'photo':
            submissions_photos.append(InputMediaPhoto(type='photo',
                                                      media=media))
        else:
            submissions_docs.append(InputMediaDocument(type='document',
                                                       media=media))

        if len(submissions_photos) == MAX_SUBMISSIONS:
            await send_other_type(submissions_docs, bot, chat_id)
            await bot.send_media_group(chat_id=chat_id,
                                       media=submissions_photos)
            await send_possible_caption(submissions_photos,
                                        int(cb.group_id),
                                        bot, vote, chat_id)
            submissions_docs.clear()
            submissions_photos.clear()
        if len(submissions_docs) == MAX_SUBMISSIONS:
            await send_other_type(submissions_photos, bot, chat_id)
            await bot.send_media_group(chat_id=chat_id,
                                       media=submissions_docs)
            await send_possible_caption(submissions_docs,
                                        int(cb.group_id),
                                        bot, vote, chat_id)
            submissions_docs.clear()
            submissions_photos.clear()

    if submissions_photos:
        await send_other_type(submissions_photos,  bot, chat_id)
        await send_possible_caption(submissions_photos,
                                    int(cb.group_id),
                                    bot, vote, chat_id)
        submissions_photos.clear()
    if submissions_docs:
        await send_other_type(submissions_docs, bot, chat_id)
        await send_possible_caption(submissions_docs,
                                    int(cb.group_id),
                                    bot, vote, chat_id)
        submissions_docs.clear()

    del submissions_photos
    del submissions_docs

async def send_possible_caption(submissions: list,
                                group_id: int,
                                bot: Bot, vote: VoteDB,
                                chat_id: int):
    caption = ''
    i = 1
    for obj in submissions:
        if isinstance(obj.media, str):
            likes, user = vote.select_all_likes_with_user(group_id,
                                                          obj.media)
            if len(user) < 2:
                continue
            print(likes, user)
            if likes is None:
                likes = 0
            caption += f"{i}) likes = {likes}, @{user[0]}, {user[1]}, {user[2]}\n"
            i += 1
    if caption:
        await bot.send_message(chat_id=chat_id, text=caption)


async def send_other_type(list_of_object: list[InputMediaDocument
                                               | InputMediaPhoto],
                          bot: Bot, msg: int):
    if len(list_of_object) == 0:
        return
    if len(list_of_object) > 1:
        await bot.send_media_group(chat_id=msg, media=list_of_object)
    elif len(list_of_object) == 1 and isinstance(list_of_object[0],
                                                 InputMediaDocument):
        await bot.send_document(chat_id=msg, document=list_of_object[0].media)
    elif len(list_of_object) == 1 and isinstance(list_of_object[0],
                                                 InputMediaPhoto):
        await bot.send_photo(chat_id=msg, photo=list_of_object[0].media)
    await async_sleep(0.5)


async def finish_contest(query: types.CallbackQuery, bot: Bot,
                         callback_data: CallbackManage, admin_unit: AdminDB):
    pass


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
    #admin_right = await admin_unit.check_admin(user.telegram_id, chat.telegram_id)
    #if admin_right is False:
    #    return

    theme = await admin_unit.get_contest_theme(chat.telegram_id)
    msg = f"Текущая тема: {theme}"
    await bot.send_message(message.chat.id, msg)


async def on_user_join(message: types.Message, bot: Bot,
                       register_unit: RegisterDB):
    user, chat = TelegramDeserialize.unpack(message,
                                            message_id_not_exists=True)

    msg, reg_msg = await i_on_user_join(register_unit=register_unit,
                                  user=user, chat=chat)

    await bot.send_message(chat.telegram_id, msg)
    if reg_msg:
        await bot.send_message(chat.telegram_id, reg_msg)
