import inquirer
from termcolor import colored
from inquirer.themes import load_theme_from_dict as loadth

from .config import *

def get_action():
    theme = {
        "Question": {
            "brackets_color": "bright_yellow"
        },
        "List": {
            "selection_color": "bright_blue"
        }
    }

    question = [
        inquirer.List(
            "action",
            message=colored("Выберите действие", 'light_yellow'),
            choices=["Получить балансы для всех токенов на кошельках", "Получить баланс только конкретного токена", "Справка", "Выход"],
        )
    ]
    action = inquirer.prompt(question, theme=loadth(theme))['action']
    return action

def select_chains(chains):
    theme = {
        "Question": {
            "brackets_color": "bright_yellow"
        },
        "List": {
            "selection_color": "bright_blue"
        }
    }

    question = [
        inquirer.Checkbox(
            "chains",
            message=colored("Выберите сети, для которых нужно получить балансы (установите галочку напротив нужных вариантов ответа с помощью клавиш стрелок <- ->)", 'light_yellow'),
            choices=["ВСЕ СЕТИ", *chains],
        )
    ]
    selected_chains = inquirer.prompt(question, theme=loadth(theme))['chains']
    if ('ВСЕ СЕТИ' in selected_chains):
        return chains
    return selected_chains

def get_ticker():
    theme = {
        "Question": {
            "brackets_color": "bright_yellow"
        },
        "List": {
            "selection_color": "bright_blue"
        }
    }

    question = [
        inquirer.Text("ticker", message=colored("Введите название (тикер) токена", 'light_yellow'))
    ]
    ticker = inquirer.prompt(question, theme=loadth(theme))['ticker'].upper()
    return ticker

def get_minimal_amount_in_usd():
    while True:
        theme = {
            "Question": {
                "brackets_color": "bright_yellow"
            },
            "List": {
                "selection_color": "bright_blue"
            }
        }

        question = [
                inquirer.Text("min_amount", message=colored("Введите минимальную сумму в $, начиная с которой токен будет отображен в таблице", 'light_yellow'), default="0.01")
        ]
        try:
            min_amount = float(inquirer.prompt(question, theme=loadth(theme))['min_amount'].strip())
            break
        except:
            logger.error('Ошибка! Неверный ввод')
    if (min_amount) == 0:
        min_amount = -1
    return min_amount


def get_num_of_threads():
    while True:
        theme = {
            "Question": {
                "brackets_color": "bright_yellow"
            },
            "List": {
                "selection_color": "bright_blue"
            }
        }

        question = [
                inquirer.Text("num_of_threads", message=colored("Количество рабочих потоков (если у вас > 100 адресов, ставьте только 1 поток)", 'light_yellow'), default="1")
        ]
        try:
            num_of_threads = int(inquirer.prompt(question, theme=loadth(theme))['num_of_threads'].strip())
            break
        except:
            logger.error('Ошибка! Неверный ввод')
    if (num_of_threads) == 0:
        num_of_threads = 3
    return num_of_threads
