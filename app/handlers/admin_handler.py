from asyncio import sleep as async_sleep
from typing import Tuple

from aiogram import Bot, types
from aiogram.types import (
    ChatMemberOwner,
    InlineKeyboardMarkup,
    InputMediaDocument,
    InputMediaPhoto,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from db.db_operations import AdminDB, ObjectFactory, VoteDB
from utils.admin_keyboard import AdminActions, AdminKeyboard, CallbackManage
from utils.TelegramUserClass import TelegramDeserialize

NO_THEME = "-1"


async def cmd_choose_group(
    message: types.Message,
    bot: Bot,
    admin_unit: AdminDB,
    msg: dict[str, dict[str, str]],
):
    if not message.text:
        return
    user, _ = TelegramDeserialize.unpack(message)
    admin_right = await admin_unit.select_all_administrated_groups(user.telegram_id)

    if len(admin_right) == 0:
        await bot.send_message(user.telegram_id, msg["admin"]["you_are_not_admin"])
        return

    builder = InlineKeyboardBuilder()
    data = CallbackManage(action=AdminActions.chosen_group, group_id="-1")

    for admin in admin_right:
        data.group_id = admin[1]
        builder.button(text=f"{admin[0]}", callback_data=data.pack())

    builder.adjust(1, 1)

    await bot.send_message(
        user.telegram_id, msg["admin"]["choose_group"], reply_markup=builder.as_markup()
    )


async def callback_back(
    query: types.CallbackQuery,
    bot: Bot,
    callback_data: CallbackManage,
    admin_unit: AdminDB,
    msg: dict[str, dict[str, str]],
):
    admin_right = await admin_unit.select_all_administrated_groups(query.from_user.id)

    if not query.message:
        query.answer("Слишком старое сообщение, запусти новое")
        return
    if len(admin_right) == 0:
        await bot.send_message(query.from_user.id, msg["admin"]["you_are_not_admin"])
        return

    builder = InlineKeyboardBuilder()
    data = callback_data
    data.action = AdminActions.chosen_group
    data.group_id = NO_THEME

    for admin in admin_right:
        data.group_id = admin[1]
        builder.button(text=f"{admin[0]}", callback_data=data.pack())

    builder.adjust(1, 1)

    await query.message.edit_text(
        text=msg["admin"]["choose_group"], reply_markup=builder.as_markup()
    )


async def cmd_action_choose(
    query: types.CallbackQuery,
    bot: Bot,
    callback_data: CallbackManage,
    admin_unit: AdminDB,
    msg: dict[str, dict[str, str]],
):
    bot_name = await bot.me()
    if not query.message or not bot_name.username:
        query.answer("Слишком старое сообщение, запусти новое")
        return
    keyboard = AdminKeyboard.fromcallback(callback_data)
    vote_in_progress = await admin_unit.get_current_vote_status(
        int(callback_data.group_id)
    )
    theme = await admin_unit.get_contest_theme(int(callback_data.group_id))
    if not theme:
        return
    is_owner = await bot.get_chat_member(
        chat_id=callback_data.group_id, user_id=query.from_user.id
    )

    keyboard_r = await choose_action_board(vote_in_progress, theme, is_owner, keyboard)

    status = await admin_unit.get_info(int(callback_data.group_id))
    info = ""
    if len(status) == 2:
        info = f"Текущая тема: {status[0]}\n" f"Количество фоток: <b>{status[1]}\n</b>"
    elif len(status) == 3:
        link_vote = ObjectFactory.build_vote_link(
            bot_name.username, callback_data.group_id
        )
        info = (
            f"Текущая тема: {status[0]}\n"
            f"Количество фоток: {status[1]}\n"
            f"Количество проголосовавших: <b>{status[2]}</b>\n"
            f"Ссылка на голосование: {link_vote}\n"
        )
    caption = info + "\n" + msg["admin"]["choose_action"]
    await query.message.edit_text(
        text=caption, reply_markup=keyboard_r, parse_mode="HTML"
    )


async def cmd_check_if_sure(
    query: types.CallbackQuery,
    callback_data: CallbackManage,
    msg: dict[str, dict[str, str]],
):
    if not query.message:
        query.answer("Слишком старое сообщение, запусти новое")
        return
    keyboard = AdminKeyboard.fromcallback(callback_data)
    await query.message.edit_text(
        text=msg["admin"]["are_you_sure_F"], reply_markup=keyboard.keyboard_are_you_sure
    )


async def cmd_check_if_sure_vote(
    query: types.CallbackQuery,
    callback_data: CallbackManage,
    msg: dict[str, dict[str, str]],
):
    if not query.message:
        query.answer("Слишком старое сообщение, запусти новое")
        return
    keyboard = AdminKeyboard.fromcallback(callback_data)
    await query.message.edit_text(
        text=msg["admin"]["are_you_sure_S"],
        reply_markup=keyboard.keyboard_are_you_sure_start,
    )


async def cmd_finish_vote(
    query: types.CallbackQuery,
    bot: Bot,
    callback_data: CallbackManage,
    admin_unit: AdminDB,
    msg: dict[str, dict[str, str]],
):
    if not query.message:
        query.answer("Слишком старое сообщение, запусти новое")
        return

    # code to refactor:

    # get theme and change status to vote_closed
    theme = await admin_unit.get_contest_theme(int(callback_data.group_id))
    if not theme:
        return
    await admin_unit.change_current_vote_status(int(callback_data.group_id))
    keyboard = AdminKeyboard.fromcallback(callback_data)
    vote = VoteDB(admin_unit.engine)

    # retrieve all contest_photo_and_ids and choose winner
    ids = await admin_unit.select_contest_photos_ids_and_types(
        int(callback_data.group_id)
    )

    # if no ids, then no photos were submitted
    if len(ids) == 0:
        await query.message.edit_text(
            text=msg["admin"]["no_photos_at_end"], reply_markup=keyboard.keyboard_back
        )
        await admin_unit.change_contest_to_none(int(callback_data.group_id))
        return

    id, user = await vote.select_winner_from_contest(int(callback_data.group_id))
    # if no votes, then no winner
    if not user:
        await query.message.edit_text(
            text=msg["vote"]["no_winner"], reply_markup=keyboard.keyboard_back
        )
        await vote.erase_all_photos(int(callback_data.group_id))
        await admin_unit.change_contest_to_none(int(callback_data.group_id))
        return

    # save winner to db and send message to group
    await admin_unit.register_winner(user[-2], int(callback_data.group_id))
    file_id = await vote.select_file_id(id)
    likes = await vote.select_all_likes_file_id(int(callback_data.group_id), file_id)
    type_photo = await vote.select_file_type_by_file_id(file_id)
    await query.message.edit_text(
        text=msg["admin"]["vote_end"], reply_markup=keyboard.keyboard_back
    )
    user_info = msg["vote"]["user_info"].format(
        theme=theme, username=user[0], full_name=user[1], likes=likes
    )
    receiver = int(callback_data.group_id)
    if user[-1] is False:
        if type_photo == "photo":
            win_msg = await bot.send_photo(
                chat_id=receiver, photo=file_id, caption=user_info
            )
        else:
            win_msg = await bot.send_document(
                chat_id=receiver, document=file_id, caption=user_info
            )
    else:
        win_msg = await bot.send_message(
            chat_id=receiver, text=msg["vote"]["many_winners"]
        )
    win_link = win_msg.get_url()
    if win_link:
        await vote.update_link_to_results(receiver, win_link)

    # send photos
    await internal_view_submissions(receiver, ids, bot, admin_unit, callback_data)

    # turn-off feature: deletes photo history
    # if user[-1] is False:
    #     try:
    #         await set_chat_photo(bot, file_id, int(callback_data.group_id), theme)
    #     except exceptions.TelegramBadRequest as e:
    #         await bot.send_message(chat_id=receiver,
    #                                text=msg["vote"]["err"])
    #         logging.warning(e)

    # delete photos and change status to none
    await vote.erase_all_photos(int(callback_data.group_id))
    await admin_unit.change_contest_to_none(int(callback_data.group_id))


# async def set_chat_photo(bot: Bot, file_id: str, group_id: int,
#                          name: str):
#     file = await bot.get_file(file_id)
#     if not file.file_path:
#         return
#     result = await bot.download_file(file.file_path, io.BytesIO())
#     if not result:
#         return
#     photo = BufferedInputFile(result.read(), filename=name)
#     await bot.set_chat_photo(chat_id=group_id,
#                                      photo=photo)


async def view_votes(
    query: types.CallbackQuery,
    bot: Bot,
    callback_data: CallbackManage,
    admin_unit: AdminDB,
):
    ids = await admin_unit.select_contest_photos_ids_and_types(
        int(callback_data.group_id)
    )
    await internal_view_submissions(
        query.from_user.id, ids, bot, admin_unit, callback_data
    )


async def view_submissions(
    query: types.CallbackQuery,
    bot: Bot,
    callback_data: CallbackManage,
    admin_unit: AdminDB,
    msg: dict[str, dict[str, str]],
):
    ids = await admin_unit.select_contest_photos_ids_and_types(
        int(callback_data.group_id)
    )
    if len(ids) == 0:
        if query.message:
            keyboard = AdminKeyboard.fromcallback(callback_data)
            await query.message.edit_text(
                msg["admin"]["no_photos_at_start"], reply_markup=keyboard.keyboard_back
            )
        return
    await internal_view_submissions(
        query.from_user.id, ids, bot, admin_unit, callback_data
    )


async def internal_view_submissions(
    chat_id: int,
    ids: list,
    bot: Bot,
    admin_unit: AdminDB,
    callback_data: CallbackManage,
):
    group_id = int(callback_data.group_id)
    if len(ids) == 1:
        if ids[0][1] == "photo":
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
        if media_type == "photo":
            submissions_photos.append(InputMediaPhoto(type="photo", media=media))
        else:
            submissions_docs.append(InputMediaDocument(type="document", media=media))

        if len(submissions_photos) == MAX_SUBMISSIONS:
            await send_photos(submissions_photos, bot, chat_id)
            await send_possible_caption(
                submissions_photos, group_id, bot, vote, chat_id
            )
            submissions_photos.clear()
        if len(submissions_docs) == MAX_SUBMISSIONS:
            await send_photos(submissions_docs, bot, chat_id)
            await send_possible_caption(submissions_docs, group_id, bot, vote, chat_id)
            submissions_docs.clear()

    if submissions_photos:
        await send_photos(submissions_photos, bot, chat_id)
        await send_possible_caption(submissions_photos, group_id, bot, vote, chat_id)
    if submissions_docs:
        await send_photos(submissions_docs, bot, chat_id)
        await send_possible_caption(submissions_docs, group_id, bot, vote, chat_id)

    del submissions_photos
    del submissions_docs


async def send_possible_caption(
    submissions: list, group_id: int, bot: Bot, vote: VoteDB, chat_id: int
):
    caption = ""
    i = 1
    for obj in submissions:
        if not isinstance(obj.media, str):
            continue
        likes, user = await vote.select_all_likes_with_user(group_id, obj.media)
        if len(user) < 2:
            continue
        if likes is None:
            likes = 0
        caption += f"{i}) Лайков - {likes}, @{user[0]}, {user[1]}\n"
        i += 1
    if caption:
        await bot.send_message(chat_id=chat_id, text=caption)


async def send_photos(
    list_of_object: list[InputMediaDocument | InputMediaPhoto], bot: Bot, msg: int
):
    if len(list_of_object) == 0:
        return
    if len(list_of_object) > 1:
        await bot.send_media_group(chat_id=msg, media=list_of_object)
    elif len(list_of_object) == 1 and isinstance(list_of_object[0], InputMediaDocument):
        await bot.send_document(chat_id=msg, document=list_of_object[0].media)
    elif len(list_of_object) == 1 and isinstance(list_of_object[0], InputMediaPhoto):
        await bot.send_photo(chat_id=msg, photo=list_of_object[0].media)
    await async_sleep(0.5)


async def choose_action_board(
    vote_in_progress: bool, theme: str, is_owner, keyboard: AdminKeyboard
):
    keyboard_options: dict[Tuple[bool, bool, bool], InlineKeyboardMarkup] = {
        (False, False, False): keyboard.keyboard_no_contest,
        (False, False, True): keyboard.keyboard_no_contest_own,
        (False, True, False): keyboard.keyboard_no_vote,
        (True, True, False): keyboard.keyboard_vote_in_progress,
        (False, True, True): keyboard.keyboard_no_vote_own,
        (True, True, True): keyboard.keyboard_vote_in_progress_own,
    }

    keyboard_r = keyboard_options.get(
        (vote_in_progress, theme != NO_THEME, isinstance(is_owner, ChatMemberOwner))
    )

    return keyboard_r
