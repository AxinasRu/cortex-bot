import json
import os

from cortex import consts

SETTINGS_FILE = f'{consts.storage_folder}/{consts.settings_file}'

os.makedirs(consts.storage_folder, exist_ok=True)

TELEGRAM = 'telegram'
OPENAI = 'openai'
PROXY = 'proxy'
settings = {
    TELEGRAM: '',
    OPENAI: '',
    PROXY: ''
}

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
