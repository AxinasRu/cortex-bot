import logging
from asyncio import sleep

import aiohttp
from aiogram import types, Bot, Dispatcher
from aiogram.utils import executor
from aiohttp import ClientError, ClientProxyConnectionError, ClientOSError, ServerDisconnectedError
from aiohttp.client import _RequestContextManager
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from cortex import manager
from cortex.db import database, tables
from cortex.manager import TELEGRAM
from cortex.messages import profile_message, translate_prompt, help_message

logging.basicConfig(level=logging.DEBUG)
bot = Bot(token=manager.settings[TELEGRAM])
dp = Dispatcher(bot)


@dp.message_handler(commands=['help', 'start'])
async def start_command(message: types.Message):
    await message.answer(help_message, parse_mode='markdown')


def round_list(floats, basis):
    return list(map(
        lambda x: 0 if x is None else round(x * (1 / basis)) / (1 / basis),
        floats
    ))


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
        func.sum(tables.Message.scan_summary)
    ).join(tables.Log, tables.Message.id == tables.Log.message_id)


@dp.message_handler(commands=['info'])
async def profile_command(message: types.Message):
    with Session(database.engine) as session:
        all_sums = round_list((await generate_query(session)).filter(
            tables.Log.user_id == message.from_user.id,
            tables.Log.chat_id == message.chat.id
        ).first(), 0.1)

        week_sums = round_list((await generate_query(session)).filter(
            tables.Log.user_id == message.from_user.id,
            tables.Log.chat_id == message.chat.id,
            tables.Log.datetime >= func.date(func.now(), '-7 days')
        ).first(), 0.1)
        await message.reply(
            profile_message(message.from_user.full_name, all_sums, week_sums),
            parse_mode='markdown'
        )


@dp.message_handler()
async def on_message(message: types.Message):
    if message.is_command() or message.from_user.is_bot:
        return
    text = message.text

    row = tables.Log(
        chat_id=message.chat.id,
        user_id=message.from_user.id
    )

    with Session(database.engine) as session:
        db_message = session.scalars(select(tables.Message).where(tables.Message.text == text)).one_or_none()
        if db_message is not None:
            row.message_id = db_message.id
            session.add(row)
            session.commit()
            return

    db_message = tables.Message(
        text=text
    )

    async with aiohttp.ClientSession() as session:
        resp_data = await process(
            translate_prompt(text),
            session,
            "https://api.openai.com/v1/chat/completions",
            lambda i: print(f'Translating {message.message_id}@{message.chat.id} - attempt {i}', flush=True)
        )

        translated: str = resp_data['choices'][0]['message']['content'].removeprefix('OUTPUT:').strip()
        db_message.translated = translated

        resp_data = await process(
            {'input': translated},
            session,
            "https://api.openai.com/v1/moderations",
            lambda i: print(f'Checking {message.message_id}@{message.chat.id} - attempt {i}', flush=True)
        )

        resp_data = resp_data['results'][0]['category_scores']
        db_message.scan_sexual = resp_data['sexual']
        db_message.scan_hate = resp_data['hate']
        db_message.scan_harassment = resp_data['harassment']
        db_message.scan_self_harm = resp_data['self-harm']
        db_message.scan_sexual_minors = resp_data['sexual/minors']
        db_message.scan_hate_threatening = resp_data['hate/threatening']
        db_message.scan_violence_graphic = resp_data['violence/graphic']
        db_message.scan_self_harm_intent = resp_data['self-harm/intent']
        db_message.scan_self_harm_instructions = resp_data['self-harm/instructions']
        db_message.scan_harassment_threatening = resp_data['harassment/threatening']
        db_message.scan_violence = resp_data['violence']

    print(f'Writing {message.message_id}@{message.chat.id}', flush=True)
    with Session(database.engine) as session:
        session.add(db_message)
        session.flush()
        session.refresh(db_message)
        row.message_id = db_message.id
        session.add(row)
        session.commit()


async def process(data, session, url, callback=lambda x: None):
    i = 1
    while True:
        callback(i)
        try:
            resp = await get_query(data, session, url)
        except ClientError as e:
            if isinstance(e, ClientProxyConnectionError):
                manager.switch_proxy()
            elif isinstance(e, OSError | ServerDisconnectedError):
                await sleep(0.1)
            else:
                print(e, flush=True)
                await sleep(5)
            continue
        if resp.status == 200:
            return await resp.json()
        elif resp.status == 429:
            print(await resp.text(), flush=True)
            if manager.check_openai():
                await sleep(25)
            else:
                manager.switch_openai()
        elif resp.status == 500 or resp.status == 503:
            await sleep(0.5)
        i += 1


def get_query(data, session, url) -> "_RequestContextManager":
    headers = {'Authorization': f'Bearer {manager.openai()}'}
    if manager.proxy() is None:
        execute = session.post(
            url,
            headers=headers,
            json=data
        )
    else:
        execute = session.post(
            url,
            proxy=manager.proxy(),
            headers=headers,
            json=data
        )
    return execute


def start() -> None:
    executor.start_polling(dp)


if __name__ == '__main__':
    start()
