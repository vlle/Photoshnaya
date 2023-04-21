from asyncio import sleep as async_sleep
from aiogram import types
from aiogram import Bot
from aiogram.types import InputMediaDocument, InputMediaPhoto
from aiogram.utils.keyboard import InlineKeyboardBuilder
from utils.TelegramUserClass import TelegramDeserialize
from handlers.internal_logic.admin import i_set_theme
from handlers.internal_logic.on_join import i_on_user_join
from db.db_operations import RegisterDB, AdminDB
from utils.admin_keyboard import AdminKeyboard, CallbackManage, AdminActions


async def callback_back(query: types.CallbackQuery, bot: Bot,
                        callback_data: CallbackManage, admin_unit: AdminDB):
    admin_right = admin_unit.select_all_administrated_groups(
            int(callback_data.user)
            )

    if not query.message:
        return
    if len(admin_right) == 0:
        msg = """Ты не являешься администратором.\n
             Чтобы стать администратором в группе --
             добавь меня с правами админа в чат."""
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
    await bot.edit_message_text(text=msg, chat_id=callback_data.user,
                                message_id=query.message.message_id,
                                reply_markup=builder.as_markup())


async def cmd_choose_group(message: types.Message, bot: Bot,
                           admin_unit: AdminDB):
    if not message.text:
        return
    user, _ = TelegramDeserialize.unpack(message)
    admin_right = admin_unit.select_all_administrated_groups(user.telegram_id)

    if len(admin_right) == 0:
        msg = """Ты не являешься администратором.\n
             Чтобы стать администратором в группе --
             добавь меня с правами админа в чат."""
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
    await bot.send_message(user.telegram_id, msg,
                           reply_markup=builder.as_markup())


async def cmd_action_choose(query: types.CallbackQuery, bot: Bot,
                            callback_data: CallbackManage,
                            admin_unit: AdminDB):

    if not query.message:
        return
    msg = 'Выберите ваше действие'
    print(callback_data)
    keyboard = AdminKeyboard.fromcallback(callback_data)
    vote_in_progress = admin_unit.get_current_vote_status(
            int(callback_data.group_id)
            )

    if not vote_in_progress:
        keyboard_r = keyboard.keyboard_no_vote
    else:
        keyboard_r = keyboard.keyboard_vote_in_progress

    await bot.edit_message_text(text=msg, chat_id=callback_data.user,
                                message_id=query.message.message_id,
                                reply_markup=keyboard_r)


async def cmd_check_if_sure(query: types.CallbackQuery, bot: Bot,
                            callback_data: CallbackManage):
    if not query.message:
        return
    keyboard = AdminKeyboard.fromcallback(callback_data)
    msg = "Точно хочешь завершить голосование?"
    await bot.edit_message_text(text=msg,
                                chat_id=callback_data.user,
                                message_id=query.message.message_id,
                                reply_markup=keyboard.keyboard_are_you_sure)


async def cmd_check_if_sure_vote(query: types.CallbackQuery, bot: Bot,
                            callback_data: CallbackManage):
    if not query.message:
        return
    keyboard = AdminKeyboard.fromcallback(callback_data)
    msg = "Точно хочешь начать голосование?"
    await bot.edit_message_text(text=msg,
                                chat_id=callback_data.user,
                                message_id=query.message.message_id,
                                reply_markup=keyboard.keyboard_are_you_sure)


async def cmd_finish_contest(query: types.CallbackQuery, bot: Bot,
                             callback_data: CallbackManage,
                             admin_unit: AdminDB):
    if not query.message:
        return
    admin_unit.change_current_vote_status(int(callback_data.group_id))
    keyboard = AdminKeyboard.fromcallback(callback_data)
    bot_link = "t.me/Photoshnaya_bot?start=" + callback_data.group_id + "_3"
    msg = f"Голосование запущено. Вот ссылка, отправьте ее в чат: {bot_link}"
    await bot.edit_message_text(text=msg,
                                chat_id=callback_data.user,
                                message_id=query.message.message_id,
                                reply_markup=keyboard.keyboard_back)


async def cmd_finish_vote(query: types.CallbackQuery, bot: Bot,
                          callback_data: CallbackManage, admin_unit: AdminDB):
    if not query.message:
        return
    admin_unit.change_current_vote_status(int(callback_data.group_id))
    keyboard = AdminKeyboard.fromcallback(callback_data)
    msg = 'Голосование завершено. Результаты:\n, отправьте их в чат'
    await bot.edit_message_text(text=msg, chat_id=callback_data.user,
                                message_id=query.message.message_id,
                                reply_markup=keyboard.keyboard_back)


async def view_votes(query: types.CallbackQuery, bot: Bot,
                     callback_data: CallbackManage, admin_unit: AdminDB):

    pass


async def view_submissions(query: types.CallbackQuery, bot: Bot,
                           callback_data: CallbackManage, admin_unit: AdminDB):
    cb = callback_data

    ids = admin_unit.select_contest_photos_ids_and_types(int(cb.group_id))
    if len(ids) == 0:
        return
    await internal_view_submissions(query.from_user.id, ids, bot)


async def internal_view_submissions(chat_id: int, ids: list, bot: Bot):
    if len(ids) == 1:
        if ids[0][1] == 'photo':
            await bot.send_photo(chat_id=chat_id, photo=ids[0][0])
        else:
            await bot.send_document(chat_id=chat_id, document=ids[0][0])
        return

    MAX_SUBMISSIONS = 10
    submissions_photos = []
    submissions_docs = []
    for id in ids:
        media_type, media = id[1], id[0]
        if media_type == 'photo':
            await send_other_type(submissions_docs, bot, chat_id)
            submissions_photos.append(InputMediaPhoto(type='photo',
                                                      media=media))
        else:
            submissions_docs.append(InputMediaDocument(type='document',
                                                       media=media))

        if len(submissions_photos) == MAX_SUBMISSIONS:
            await send_other_type(submissions_docs, bot, chat_id)
            await bot.send_media_group(chat_id=chat_id,
                                       media=submissions_photos)
            submissions_photos.clear()
        if len(submissions_docs) == MAX_SUBMISSIONS:
            await send_other_type(submissions_photos, bot, chat_id)
            await bot.send_media_group(chat_id=chat_id,
                                       media=submissions_docs)
            submissions_docs.clear()

    if submissions_photos:
        await send_other_type(submissions_photos,  bot, chat_id)
    if submissions_docs:
        await send_other_type(submissions_docs, bot, chat_id)

    del submissions_photos
    del submissions_docs


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
    list_of_object.clear()
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
    admin_right = admin_unit.check_admin(user.telegram_id, chat.telegram_id)
    if admin_right is False:
        return

    theme = admin_unit.get_contest_theme(chat.telegram_id)
    msg = f"Текущая тема: {theme}"
    await bot.send_message(message.chat.id, msg)


async def on_user_join(message: types.Message, bot: Bot,
                       register_unit: RegisterDB):
    user, chat = TelegramDeserialize.unpack(message,
                                            message_id_not_exists=True)

    msg, reg_msg = i_on_user_join(register_unit=register_unit,
                                  user=user, chat=chat)

    await bot.send_message(chat.telegram_id, msg)
    if reg_msg:
        await bot.send_message(chat.telegram_id, reg_msg)
