import asyncio
import logging
import os
import pathlib
import tomllib

from aiogram import Bot, Dispatcher, F
from aiogram.filters import JOIN_TRANSITION, ChatMemberUpdatedFilter, Command
from aiogram.types import (
    BotCommand,
    BotCommandScopeAllGroupChats,
    BotCommandScopeAllPrivateChats,
)
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine

from db.db_classes import Base
from db.db_operations import AdminDB, LikeDB, ObjectFactory, RegisterDB
from handlers.admin_add_fsm import AdminAdd, set_admin, set_admin_accept_message
from handlers.admin_del_fsm import AdminDel, del_admin, del_admin_accept_message
from handlers.admin_handler import (
    callback_back,
    cmd_action_choose,
    cmd_check_if_sure,
    cmd_check_if_sure_vote,
    cmd_choose_group,
    cmd_finish_vote,
    view_submissions,
    view_votes,
)
from handlers.contest_fsm import (
    ContestCreate,
    set_theme,
    set_theme_accept_message,
    should_i_post_theme,
)
from handlers.delete_submission import (
    DeletePhoto,
    delete_photo_r_u_sure,
    delete_submission,
    make_delete_decision,
    set_admin_delete_photo,
)
from handlers.on_join import on_user_join
from handlers.personal_vote_menu import callback_back as callback_back_vote
from handlers.personal_vote_menu import (
    callback_choose_photo,
    callback_next,
    callback_prev,
    callback_send_vote,
    callback_set_like,
    callback_set_no_like,
    cmd_start,
    get_file_id,
)
from handlers.user_action import register_photo, view_leaders, view_overall_participants
from handlers.vote_start_fsm import VoteStart, set_vote, should_i_post_vote
from reminders import send_reminders
from utils.admin_keyboard import AdminActions, CallbackManage
from utils.keyboard import Actions, CallbackVote


async def main():
    load_dotenv()
    token = os.environ.get("token")
    if not token:
        logging.critical("No token")
        return

    ps_url = os.environ.get("ps_url")
    if not ps_url:
        logging.critical("No postgre_url")
        return

    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(message)s",
        level=logging.INFO,
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    bot = Bot(token=token)
    dp = Dispatcher()
    text_toml = (
        pathlib.Path(__file__).absolute().parent
        / "handlers"
        / "handlers_text"
        / "text.toml"
    )
    with open(text_toml, "rb") as f:
        msg = tomllib.load(f)

    engine = create_async_engine(ps_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    register = RegisterDB(engine)
    like_engine = LikeDB(engine)
    obj_factory = ObjectFactory()
    admin_unit = AdminDB(engine)

    dp.message.register(
        register_photo, F.caption_entities & ~(F.chat.type == "private")
    )
    dp.edited_message.register(
        register_photo, F.caption_entities & ~(F.chat.type == "private")
    )

    dp.message.register(get_file_id, Command(commands=["get_file_id"]))
    dp.message.register(cmd_start, Command(commands=["start"]))
    dp.my_chat_member.register(
        on_user_join, ChatMemberUpdatedFilter(member_status_changed=JOIN_TRANSITION)
    )

    dp.callback_query.register(
        callback_next, CallbackVote.filter(F.action == Actions.next_text)
    )
    dp.callback_query.register(
        callback_prev, CallbackVote.filter(F.action == Actions.prev_text)
    )
    dp.callback_query.register(
        callback_set_like, CallbackVote.filter(F.action == Actions.no_like_text)
    )
    dp.callback_query.register(
        callback_set_no_like, CallbackVote.filter(F.action == Actions.like_text)
    )
    dp.callback_query.register(
        callback_choose_photo, CallbackVote.filter(F.action == Actions.count)
    )
    dp.callback_query.register(
        callback_back_vote, CallbackVote.filter(F.action == Actions.back_text)
    )
    dp.callback_query.register(
        callback_send_vote, CallbackVote.filter(F.action == Actions.finish_text)
    )

    ## dp.errors register
    dp.message.register(cmd_choose_group, Command(commands=["admin"]))
    dp.message.register(view_leaders, Command(commands=["leaderboards"]))
    dp.message.register(view_overall_participants, Command(commands=["view_all"]))
    dp.callback_query.register(
        callback_back, CallbackManage.filter(F.action == AdminActions.back)
    )
    dp.callback_query.register(
        cmd_action_choose, CallbackManage.filter(F.action == AdminActions.chosen_group)
    )
    dp.callback_query.register(
        cmd_check_if_sure_vote,
        CallbackManage.filter(F.action == AdminActions.finish_contest_id),
    )

    dp.callback_query.register(
        set_vote, CallbackManage.filter(F.action == AdminActions.sure_start_vote_id)
    )

    dp.callback_query.register(
        view_submissions,
        CallbackManage.filter(F.action == AdminActions.view_submissions_id),
    )
    dp.callback_query.register(
        view_votes, CallbackManage.filter(F.action == AdminActions.view_votes_id)
    )
    dp.callback_query.register(
        cmd_check_if_sure,
        CallbackManage.filter(F.action == AdminActions.finish_vote_id),
    )

    dp.callback_query.register(
        cmd_finish_vote,
        CallbackManage.filter(F.action == AdminActions.sure_finish_vote_id),
    )

    dp.callback_query.register(
        delete_submission,
        CallbackManage.filter(F.action == AdminActions.delete_submission_id),
    )
    dp.callback_query.register(
        set_theme, CallbackManage.filter(F.action == AdminActions.start_contest_id)
    )
    dp.callback_query.register(
        set_admin, CallbackManage.filter(F.action == AdminActions.add_admin_id)
    )
    dp.callback_query.register(
        del_admin, CallbackManage.filter(F.action == AdminActions.delete_admin_id)
    )

    dp.message.register(set_theme_accept_message, ContestCreate.name_contest)
    dp.message.register(should_i_post_theme, ContestCreate.will_you_post)
    dp.message.register(should_i_post_vote, VoteStart.will_you_post)

    dp.message.register(set_admin_accept_message, AdminAdd.send_admin)
    dp.message.register(del_admin_accept_message, AdminDel.send_admin)

    dp.message.register(set_admin_delete_photo, DeletePhoto.send_photo_owner)
    dp.message.register(delete_photo_r_u_sure, DeletePhoto.are_you_sure)
    dp.message.register(make_delete_decision, DeletePhoto.wait_for_confirmation)
    admin: BotCommand = BotCommand(
        command="/admin", description="Команда для вызова админской панели"
    )
    view_leader: BotCommand = BotCommand(
        command="/leaderboards", description="Посмотреть топ победителей"
    )
    view_all: BotCommand = BotCommand(
        command="/view_all", description="Посмотреть топ по участию"
    )
    await bot.set_my_commands(
        [admin], scope=BotCommandScopeAllPrivateChats()  # type: ignore
    )
    await bot.set_my_commands(
        [view_leader, view_all], scope=BotCommandScopeAllGroupChats()  # type: ignore
    )

    await asyncio.gather(
        dp.start_polling(
            bot,
            engine=engine,
            register_unit=register,
            obj_factory=obj_factory,
            admin_unit=admin_unit,
            like_engine=like_engine,
            msg=msg,
        ),
        send_reminders(bot, msg["contest"]["reminder"]),
    )
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
