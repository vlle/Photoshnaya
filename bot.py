import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message

# Включаем логирование, чтобы не пропустить важные сообщения
logging.basicConfig(level=logging.INFO)
# Объект бота
bot = Bot(token="5811948834:AAGl_bFk61wHJXeS2nHLihcAVTAbwMT55JA")
# Диспетчер
dp = Dispatcher()

# Хэндлер на команду /start
@dp.message((Command(commands=["start"])))
async def cmd_start(message: types.Message):
    await message.answer("Hello!")

# Запуск процесса поллинга новых апдейтов
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

