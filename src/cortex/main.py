import logging

import aiohttp
from aiogram import types, Bot, Dispatcher
from aiogram.utils import executor
from sqlalchemy.orm import Session

from cortex import manager
from cortex.db import database, tables
from cortex.manager import TELEGRAM, OPENAI, PROXY

logging.basicConfig(level=logging.DEBUG)
bot = Bot(token=manager.settings[TELEGRAM])
dp = Dispatcher(bot)


@dp.message_handler(content_types=['new_chat_members'])
async def on_join(message: types.Message):
    for chat_member in message.new_chat_members:
        if chat_member.id == (await bot.get_me()).id:
            print(f'Initializing "{message.chat.full_name}" chat')
            with Session(database.engine) as session:
                session.add(tables.Chat(
                    id=message.chat.id
                ))
                session.commit()
            print(f'Chat inited')


@dp.message_handler()
async def on_message(message: types.Message):
    if message.is_command():
        return
    text = message.md_text
    row = tables.Message(
        chat_id=message.chat.id,
        text=text
    )

    async with aiohttp.ClientSession() as session:
        url = "https://api.openai.com/v1/moderations"
        headers = {'Authorization': f'Bearer {manager.settings[OPENAI]}'}
        data = {'input': text}
        if manager.settings[PROXY] == '':
            execute = session.post(
                url,
                headers=headers,
                json=data
            )
        else:
            execute = session.post(
                url,
                proxy=manager.settings[PROXY],
                headers=headers,
                json=data
            )
        resp = await execute
        row.scan_result = resp.text()

    with Session(database.engine) as session:
        session.add(row)
        session.commit()
    print('Result received')

def start():
    executor.start_polling(dp)


if __name__ == '__main__':
    start()
