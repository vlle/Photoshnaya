import asyncio
import logging
import os
import tomllib
from dotenv import load_dotenv

from aiogram import F
from aiogram.filters import JOIN_TRANSITION
from aiogram import Bot, Dispatcher
from aiogram.filters import Command, ChatMemberUpdatedFilter

from sqlalchemy.ext.asyncio import create_async_engine
from utils.admin_keyboard import AdminActions, CallbackManage

from utils.keyboard import Actions, CallbackVote

from db.db_operations import LikeDB, ObjectFactory, RegisterDB, AdminDB
from db.db_classes import Base

from handlers.admin_handler import ContestCreate, callback_back,\
        cmd_action_choose, cmd_check_if_sure,\
        cmd_check_if_sure_vote,\
        cmd_choose_group, cmd_finish_contest, cmd_finish_vote,\
        set_theme,\
        on_user_join, set_theme_accept_message, view_submissions, view_votes
from handlers.personal_vote_menu import cmd_start, callback_next, \
        callback_set_no_like, callback_set_like, callback_prev, callback_send_vote
from handlers.user_action import register_photo


async def main():
    load_dotenv()
    token = os.environ.get('token')
    if not token:
        logging.critical("No token")
        return

    ps_url = os.environ.get('ps_url')
    if not ps_url:
        logging.critical("No postgre_url")
        return

    logging.basicConfig(level=logging.INFO)
    bot = Bot(token=token)
    dp = Dispatcher()
    with open("handlers/handlers_text/text.toml", "rb") as f:
        msg = tomllib.load(f)

    engine = create_async_engine(ps_url, echo=True)
    async with engine.begin() as conn:
        # await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    register = RegisterDB(engine)
    like_engine = LikeDB(engine)
    obj_factory = ObjectFactory()
    admin_unit = AdminDB(engine)

    dp.message.register(register_photo, F.caption_entities)
    dp.edited_message.register(register_photo, F.caption_entities)

    dp.message.register(cmd_start, Command(commands=["start"]))
    dp.my_chat_member.register(on_user_join, ChatMemberUpdatedFilter
                               (member_status_changed=JOIN_TRANSITION))

    dp.callback_query.register(callback_next, CallbackVote.filter
                               (F.action == Actions.next_text))
    dp.callback_query.register(callback_prev, CallbackVote.filter
                               (F.action == Actions.prev_text))
    dp.callback_query.register(callback_set_like, CallbackVote.filter
                               (F.action == Actions.no_like_text))
    dp.callback_query.register(callback_set_no_like, CallbackVote.filter
                               (F.action == Actions.like_text))
    dp.callback_query.register(callback_send_vote, CallbackVote.filter
                               (F.action == Actions.finish_text))

    ## dp.errors register
    dp.message.register(cmd_choose_group, Command(commands=["admin"]))
    dp.callback_query.register(callback_back, CallbackManage.filter
                               (F.action == AdminActions.back))
    dp.callback_query.register(cmd_action_choose, CallbackManage.filter
                               (F.action == AdminActions.chosen_group))
    dp.callback_query.register(cmd_check_if_sure_vote, CallbackManage.filter
                               (F.action == AdminActions.finish_contest_id))
    dp.callback_query.register(cmd_finish_contest, CallbackManage.filter
                               (F.action == AdminActions.sure_start_vote_id))
    dp.callback_query.register(view_submissions, CallbackManage.filter
                               (F.action == AdminActions.view_submissions_id))
    dp.callback_query.register(view_votes, CallbackManage.filter
                               (F.action == AdminActions.view_votes_id))
    dp.callback_query.register(cmd_check_if_sure, CallbackManage.filter
                               (F.action == AdminActions.finish_vote_id))
    dp.callback_query.register(cmd_finish_vote, CallbackManage.filter
                               (F.action == AdminActions.sure_finish_vote_id))
    dp.callback_query.register(set_theme, CallbackManage.filter
                               (F.action == AdminActions.start_contest_id))
    dp.message.register(set_theme_accept_message, ContestCreate.name_contest)

    await asyncio.gather(dp.start_polling(bot, engine=engine,
                                          register_unit=register,
                                          obj_factory=obj_factory,
                                          admin_unit=admin_unit,
                                          like_engine=like_engine,
                                          msg=msg))
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
