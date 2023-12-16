import asyncio
from asyncio import sleep

import aiohttp
from aiogram import types, Bot, Dispatcher
from aiohttp import ClientError, ClientProxyConnectionError, ServerDisconnectedError
from aiohttp.client_exceptions import ClientHttpProxyError
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from cortex import manager
from cortex.db import database, tables
from cortex.manager import TELEGRAM
from cortex.messages import profile_message, help_message, translate_prompt

# logging.basicConfig(level=logging.DEBUG)
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

    with Session(database.engine) as session:
        db_message = session.scalars(select(tables.Message).where(tables.Message.text == text)).one_or_none()
        if db_message is not None:
            session.add(tables.Log(
                chat_id=message.chat.id,
                user_id=message.from_user.id,
                message_id=db_message.id
            ))
        else:
            session.add(tables.Queue(
                chat_id=message.chat.id,
                user_id=message.from_user.id,
                text=text
            ))
        session.commit()


async def process(scope_id: int, data, session, url, callback: (lambda x: int)):
    attempt = 0
    while True:
        attempt += 1
        callback(attempt)
        try:
            resp = await get_query(scope_id, data, session, url)
        except ServerDisconnectedError:
            await sleep(0.1)
            continue
        except (ClientProxyConnectionError, ClientHttpProxyError):
            manager.switch_proxy()
            continue
        except ClientError as e:
            print(type(e), flush=True)
            print(e, flush=True)
            await sleep(5)
            continue
        except Exception as e:
            print(type(e), flush=True)
            print(e, flush=True)
            continue
        if resp.status == 502:
            manager.switch_proxy()
        elif resp.status == 200:
            return await resp.json()
        elif resp.status == 429:
            print(await resp.text(), flush=True)
            if manager.check_openai(scope_id):
                await sleep(25)
            else:
                manager.switch_openai(scope_id)
        elif resp.status == 500 or resp.status == 503:
            await sleep(0.5)
        else:
            print(resp.status, flush=True)
            print(resp.text(), flush=True)


def get_query(scope_id, data, session, url):
    headers = {'Authorization': f'Bearer {manager.openai(scope_id)}'}
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


async def queue_poller(scope_id: int) -> None:
    while True:
        with Session(database.engine) as session:
            queue_unit = session.scalars(
                select(tables.Queue)
                .where(tables.Queue.status == 'in_queue')
            ).first()
            if queue_unit is None:
                await asyncio.sleep(1)
                continue

            if session.execute(
                    update(tables.Queue).where(
                        tables.Queue.id == queue_unit.id and tables.Queue.status == 'in_queue'
                    ).values(status='in_work')
            ).rowcount == 0:
                continue

            total_rows = session.query(func.count(tables.Queue.id)).scalar()

        db_message = tables.Message(
            text=queue_unit.text
        )

        async with aiohttp.ClientSession() as session:
            resp_data = await process(
                scope_id,
                translate_prompt(queue_unit.text),
                session,
                "https://api.openai.com/v1/chat/completions",
                lambda i: print(f'{scope_id} - translating {queue_unit.id}/{total_rows} - attempt {i}', flush=True)
            )

            translated: str = resp_data['choices'][0]['message']['content'].removeprefix('OUTPUT:').strip()
            db_message.translated = translated

            resp_data = await process(
                scope_id,
                {'input': translated},
                session,
                "https://api.openai.com/v1/moderations",
                lambda i: print(f'{scope_id} - checking {queue_unit.id}/{total_rows} - attempt {i}', flush=True)
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

        print(f'{scope_id} - writing {queue_unit.id}/{total_rows}', flush=True)
        with Session(database.engine) as session:
            try:
                session.add(db_message)
                session.flush()
                session.refresh(db_message)
                session.add(tables.Log(
                    chat_id=queue_unit.chat_id,
                    user_id=queue_unit.user_id,
                    message_id=db_message.id
                ))
            except IntegrityError as e:
                print(e)
                session.rollback()
            queue_unit.status = 'done'
            session.add(queue_unit)
            session.commit()


def entrypoint():
    loop = asyncio.get_event_loop()
    loop.create_task(dp.start_polling())
    for scope_id in range(manager.openai_scopes()):
        loop.create_task(queue_poller(scope_id))
    loop.run_forever()


if __name__ == '__main__':
    entrypoint()
