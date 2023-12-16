import json
import os

from cortex import consts

SETTINGS_FILE = f'{consts.storage_folder}/{consts.settings_file}'

os.makedirs(consts.storage_folder, exist_ok=True)

TELEGRAM = 'telegram'
OPENAI = 'openai'
PROXIES = 'proxies'
settings = {
    TELEGRAM: '',
    OPENAI: [
        []
    ],
    PROXIES: []
}

try:
    with open(SETTINGS_FILE, 'r') as rf:
        read = rf.read()
        if read != '':
            settings = json.loads(read)
except IOError:
    with open(SETTINGS_FILE, 'w') as file:
        json.dump(settings, file, sort_keys=True, indent=2)
    print("Insert tokens", flush=True)
    exit()
if settings[TELEGRAM] == '' or len(settings[OPENAI]) == 0:
    print("Insert tokens", flush=True)
    exit()

proxy_id = 0
openai_ids = [0] * len(settings[OPENAI])


def proxy() -> str | None:
    if len(settings[PROXIES]) == 0:
        return None
    return settings[PROXIES][proxy_id]


def switch_proxy():
    global proxy_id
    proxy_id = (proxy_id + 1) % len(settings[PROXIES])
    print(f'Switching proxy to {proxy_id + 1}', flush=True)


def openai_scopes() -> int:
    return len(settings[OPENAI])


def openai(scope: int) -> str:
    return settings[OPENAI][scope][openai_ids[scope]]


def check_openai(scope: int):
    return len(settings[OPENAI][scope]) == 1


def switch_openai(scope: int):
    global openai_ids
    openai_ids[scope] = (openai_ids[scope] + 1) % len(settings[OPENAI][scope])
    print(f'Switching openai to {openai_ids[scope] + 1}', flush=True)
