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
    OPENAI: '',
    PROXIES: []
}
proxy_id = 0

try:
    with open(SETTINGS_FILE, 'r') as rf:
        read = rf.read()
        if read != '':
            settings = json.loads(read)
except IOError:
    with open(SETTINGS_FILE, 'w') as file:
        json.dump(settings, file, sort_keys=True, indent=2)
    print("Insert token")
    exit()
if settings[TELEGRAM] == '' or settings[OPENAI] == '':
    print("Insert tokens")
    exit()


@property
def proxy() -> str | None:
    if len(settings[PROXIES]) == 0:
        return None
    return settings[PROXIES][proxy_id]


def switch_proxy():
    print('Switching proxy')
    global proxy_id
    proxy_id = (proxy_id + 1) % len(settings[PROXIES])
