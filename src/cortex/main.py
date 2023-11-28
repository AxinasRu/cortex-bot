import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher

from cortex import manager

logging.basicConfig(level=logging.INFO)
bot = Bot(token=manager.settings['telegram'])
dp = Dispatcher()


async def run_bot() -> None:
    await dp.start_polling(bot)


def start():
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(run_bot())


if __name__ == '__main__':
    start()
