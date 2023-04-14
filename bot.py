import configparser
import asyncio
import logging

from aiogram import F
from aiogram.filters import JOIN_TRANSITION
from aiogram import Bot, Dispatcher
from aiogram.filters import Command, ChatMemberUpdatedFilter

from sqlalchemy import create_engine

from utils.keyboard import Actions, CallbackVote

from db.db_classes import Base


from handlers.admin_handler import set_theme, get_theme, on_user_join
from handlers.vote import finish_contest
from handlers.personal_vote_menu import cmd_start, callback_next, callback_set_no_like, callback_set_like, callback_prev
from handlers.user_action import register_photo



async def main():
    logging.basicConfig(level=logging.INFO)
    config = configparser.ConfigParser()
    config.read('config.txt')
    token = config['DEFAULT']['token']
    bot = Bot(token=token)
    dp = Dispatcher()
    engine = create_engine("sqlite+pysqlite:///photo.db", echo=True)
    Base.metadata.create_all(engine)

    dp.message.register(register_photo, F.caption_entities)
    dp.edited_message.register(register_photo, F.caption_entities)

    dp.message.register(finish_contest, Command(commands=["finish_contest"]))
    dp.message.register(cmd_start, Command(commands=["start"]))
    dp.message.register(get_theme, Command(commands=["get_theme"]))
    dp.message.register(set_theme, Command(commands=["set_theme"]))
    dp.my_chat_member.register(on_user_join, ChatMemberUpdatedFilter(member_status_changed=JOIN_TRANSITION))

    dp.callback_query.register(callback_next, CallbackVote.filter(F.action == Actions.next))
    dp.callback_query.register(callback_prev, CallbackVote.filter(F.action == Actions.prev))
    dp.callback_query.register(callback_set_like, CallbackVote.filter(F.action == Actions.no_like))
    dp.callback_query.register(callback_set_no_like, CallbackVote.filter(F.action == Actions.like))
    await asyncio.gather(dp.start_polling(bot, engine=engine))

if __name__ == "__main__":
    asyncio.run(main())


