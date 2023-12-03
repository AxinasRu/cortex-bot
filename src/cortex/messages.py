help_message = ("*Приветсвую!*\n"
                "Данный бот является анонимным собирателем статистики с чатов. "
                "Единственная его цель - анализировать каждое сообщение на выявление негативных сообщений. "
                "С результатом статистики можно ознакомиться по командам:\n"
                "/info (узнать сколько баллов вы набрали по отдельным категориям)\n"
                "/untop (топ людей по сумме категорий)\n\n"
                "По каждой категории за каждое сообщение можно набрать от *0 до 1 балла*, а *суммарно 11 баллов*.\n"
                "Категории можно узнать по [ссылке](https://telegra.ph/Kategorii-avtomoderacii-OpenAI-12-03)")


def profile_message(user, all_sums, week_sums):
    return rf"""*{user}, твоё количество баллов на данный момент*

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
\* Суммарно - {all_sums[11]}"""


def translate_prompt(text):
    return {
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
