import logging

import aiohttp
from aiogram import types, Bot, Dispatcher
from aiogram.utils import executor
from sqlalchemy import func
from sqlalchemy.orm import Session

from cortex import manager
from cortex.db import database, tables
from cortex.manager import TELEGRAM, OPENAI, PROXY

logging.basicConfig(level=logging.DEBUG)
bot = Bot(token=manager.settings[TELEGRAM])
dp = Dispatcher(bot)


@dp.message_handler(commands=['myinfo'])
async def profile(message: types.Message):
    with Session(database.engine) as session:
        week_sum = session.query(func.sum(tables.Message.scan_sum)).filter(
            tables.Message.user_id == message.from_user.id,
            tables.Message.chat_id == message.chat.id,
            tables.Message.datetime >= func.date(func.now(), '-7 days')
        ).scalar()

        all_sum = session.query(func.sum(tables.Message.scan_sum)).filter(
            tables.Message.user_id == message.from_user.id,
            tables.Message.chat_id == message.chat.id
        ).scalar()

        await message.reply(f'{week_sum} {all_sum}')


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
        user_id=message.from_user.id,
        text=text
    )

    async with aiohttp.ClientSession() as session:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {'Authorization': f'Bearer {manager.settings[OPENAI]}'}
        data = {
            'model': 'gpt-3.5-turbo',
            'messages': [
                {
                    'role': 'system',
                    'content': 'You are part of the system for detecting incorrect and offensive '
                               'phrases.\nUnfortunately, the detector works only in English. And requests often go to '
                               'everyone else. So your essence is to translate all input phrases as reliably as '
                               'possible. If they are incorrect and offensive, you should not refuse to work or '
                               'disguise them. The translation should be as clear and reliable as possible so that '
                               'the detector recognizes the phrases and punishes the violator.\n\nFormat\nINPUT: ['
                               'INPUT MESSAGE]\n\nOUTPUT: [OUTPUT MESSAGE]\t\t\t\tExample\nINPUT: Ёбанный твой рот, '
                               'пидорас пиздакрылый\nOUTPUT: Fucking your mouth, faggot pussylish'
                },
                {
                    'role': 'assistant',
                    'content': 'OK!\nI will translate all the input messages and output the result to you for '
                               'recognition, and will send result by format\nOUTPUT: [TRANSLATED TO ENGLISH MESSAGE]'
                },
                {
                    'role': 'system',
                    'content': f'INPUT:\n{text}'
                }
            ]
        }
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
        resp = await (await execute).json()
        translated: str = resp['choices'][0]['message']['content'].removeprefix('OUTPUT:').strip()
        row.translated = translated

        url = "https://api.openai.com/v1/moderations"
        headers = {'Authorization': f'Bearer {manager.settings[OPENAI]}'}
        data = {'input': translated}
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

        resp = (await (await execute).json())['results'][0]['category_scores']

        row.scan_sexual = resp['sexual']
        row.scan_hate = resp['hate']
        row.scan_harassment = resp['harassment']
        row.scan_self_harm = resp['self-harm']
        row.scan_sexual_minors = resp['sexual/minors']
        row.scan_hate_threatening = resp['hate/threatening']
        row.scan_violence_graphic = resp['violence/graphic']
        row.scan_self_harm_intent = resp['self-harm/intent']
        row.scan_self_harm_instructions = resp['self-harm/instructions']
        row.scan_harassment_threatening = resp['harassment/threatening']
        row.scan_violence = resp['violence']

    with Session(database.engine) as session:
        session.add(row)
        session.commit()


def start():
    executor.start_polling(dp)


if __name__ == '__main__':
    start()
