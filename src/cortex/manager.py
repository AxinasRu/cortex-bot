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
    OPENAI: [],
    PROXIES: []
}
proxy_id = 0
openai_id = 0

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


def proxy() -> str | None:
    if len(settings[PROXIES]) == 0:
        return None
    return settings[PROXIES][proxy_id]


def openai() -> str:
    return settings[OPENAI][openai_id]


def switch_proxy():
    global proxy_id
    proxy_id = (proxy_id + 1) % len(settings[PROXIES])
    print(f'Switching proxy to {proxy_id + 1}', flush=True)


def switch_openai():
    global openai_id
    openai_id = (openai_id + 1) % len(settings[OPENAI])
    print(f'Switching openai to {openai_id + 1}', flush=True)


def check_openai():
    return len(settings[OPENAI]) == 1
