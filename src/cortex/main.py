import logging
from asyncio import sleep

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


@dp.message_handler(commands=['info'])
async def profile(message: types.Message):
    with Session(database.engine) as session:
        all_sums = round_list((await generate_query(session)).filter(
            tables.Message.user_id == message.from_user.id,
            tables.Message.chat_id == message.chat.id
        ).first())

        week_sums = round_list((await generate_query(session)).filter(
            tables.Message.user_id == message.from_user.id,
            tables.Message.chat_id == message.chat.id,
            tables.Message.datetime >= func.date(func.now(), '-7 days')
        ).first())

        await message.reply(f"""*{message.from_user.full_name}, твоё количество баллов на данный момент*
        
*За последние 7 дней:*
\* Ненависть - {week_sums[0]}
\* Ненависть/угрожающий - {week_sums[1]}
\* Домогательство - {week_sums[2]}
\* Домогательство/угрожающий - {week_sums[3]}
\* Поощрение селфхарма - {week_sums[4]}
\* Селфхарм - {week_sums[5]}
\* Инструкции селфхарма - {week_sums[6]}
\* Сексуальное - {week_sums[7]}
\* Сексуальное несоверш. - {week_sums[8]}
\* Насилие - {week_sums[9]}
\* Описание насилия - {week_sums[10]}
\* Суммарно - {week_sums[11]}

*За всё время:*
\* Ненависть - {all_sums[0]}
\* Ненависть/угрожающий - {all_sums[1]}
\* Домогательство - {all_sums[2]}
\* Домогательство/угрожающий - {all_sums[3]}
\* Поощрение селфхарма - {all_sums[4]}
\* Селфхарм - {all_sums[5]}
\* Инструкции селфхарма - {all_sums[6]}
\* Сексуальное - {all_sums[7]}
\* Сексуальное несоверш. - {all_sums[8]}
\* Насилие - {all_sums[9]}
\* Описание насилия - {all_sums[10]}
\* Суммарно - {all_sums[11]}
        """, parse_mode='markdown')


async def generate_query(session):
    return session.query(
        func.sum(tables.Message.scan_hate),
        func.sum(tables.Message.scan_hate_threatening),
        func.sum(tables.Message.scan_harassment),
        func.sum(tables.Message.scan_harassment_threatening),
        func.sum(tables.Message.scan_self_harm),
        func.sum(tables.Message.scan_self_harm_intent),
        func.sum(tables.Message.scan_self_harm_instructions),
        func.sum(tables.Message.scan_sexual),
        func.sum(tables.Message.scan_sexual_minors),
        func.sum(tables.Message.scan_violence),
        func.sum(tables.Message.scan_violence_graphic),
        func.sum(tables.Message.scan_sum)
    )


def round_list(l):
    return list(map(
        lambda x: 0 if x is None else round(x * 10) / 10,
        l
    ))


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
    if message.is_command() or message.from_user.is_bot:
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

        while True:
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
            resp = (await execute)
            resp_data = await resp.json()
            if resp.status == 200:
                break
            if resp.status == 429:
                await sleep(25)
                continue
            if resp.status == 500 or resp.status == 503:
                await sleep(0.5)
                continue

        translated: str = resp_data['choices'][0]['message']['content'].removeprefix('OUTPUT:').strip()
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

        resp_data = (await (await execute).json())['results'][0]['category_scores']

        row.scan_sexual = resp_data['sexual']
        row.scan_hate = resp_data['hate']
        row.scan_harassment = resp_data['harassment']
        row.scan_self_harm = resp_data['self-harm']
        row.scan_sexual_minors = resp_data['sexual/minors']
        row.scan_hate_threatening = resp_data['hate/threatening']
        row.scan_violence_graphic = resp_data['violence/graphic']
        row.scan_self_harm_intent = resp_data['self-harm/intent']
        row.scan_self_harm_instructions = resp_data['self-harm/instructions']
        row.scan_harassment_threatening = resp_data['harassment/threatening']
        row.scan_violence = resp_data['violence']

    with Session(database.engine) as session:
        session.add(row)
        session.commit()


def start():
    executor.start_polling(dp)


if __name__ == '__main__':
    start()
