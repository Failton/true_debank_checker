import threading
import openpyxl

from queue import Queue
from time import time

from art import text2art
from alive_progress import alive_bar

from app.excel import *
from app.questions import *
from app.config import *
from app.utils import *


def chain_balance(node_process, session, address, chain, ticker, min_amount):
    coins = []

    payload = {
        'user_addr': address,
        'chain': chain
    }
    edit_session_headers(node_process, session, payload, 'GET', '/token/balance_list')

    resp = send_request(
        node_process, 
        session=session,
        method='GET',
        url=f'https://api.debank.com/token/balance_list?user_addr={address}&chain={chain}',
    )

    for coin in resp.json()['data']:
        if (ticker == None or coin['optimized_symbol'] == ticker):
            coin_in_usd = '?' if (coin["price"] is None) else coin["amount"] * coin["price"]
            if (type(coin_in_usd) is str or (type(coin_in_usd) is float and coin_in_usd > min_amount)):
                coins.append({
                    'amount': coin['amount'],
                    'name': coin['name'],
                    'ticker': coin['optimized_symbol'],
                    'price': coin['price'],
                    'logo_url': coin['logo_url']
                })
    
    return coins


def show_help():
    print('--------------------- СПРАВКА ---------------------\n> Что значит минимальная сумма токена в $?\n> Если токен будет иметь сумму в долларах, которая будет меньше чем указанное мин\
имальное количество - он не будет занесён в таблицу\n\n> Как выбрать все сети?\n> При выборе сетей укажите пункт "ВСЕ СЕТИ" (стрелка вправо) и нажмите энтер\n\n> Что такое число рабочих потоков?\n> Это число "рабочих процессов", которые будут одновременно получать информацию по кошелькам. Чем больше потоков - тем выше шанс получить по заднице от Cloudflare. Оптимально - 3 потока\n\n> Не двигается шкала получения баланса, что делать?\n> Уменьшать число рабочих потоков / проверять наличие интернета\n\n> В чем отличия столбцов "CHAINS" и "TOTAL"?\n> Первое - это сумма монет в $ в выбранных сетях и пулах, второе - сумма монет в $ во всех сетях\n\n> Почему получение списка использованных на кошельках сетей такое долгое?\n> Потому что на данный запрос очень сильно ругается Cloudflare, поэтому работа стоит в однопоточном режиме\n\n> Другие вопросы?\n> Пиши нам в чатик https://t.me/cryptogovnozavod_chat\n--------------------- СПРАВКА ---------------------\n')


def get_used_chains(node_process, session, address):
    payload = {
        'id': address,
    }
    edit_session_headers(node_process, session, payload, 'GET', '/user/used_chains')

    resp = send_request(
        node_process, 
        session=session,
        method='GET',
        url=f'https://api.debank.com/user/used_chains?id={address}',
    )

    chains = resp.json()['data']['chains']

    return chains


def get_chains(node_process, session, wallets):
    chains = set()

    with alive_bar(len(wallets)) as bar:
        for wallet in wallets:
            chains = chains.union(get_used_chains(node_process, session, wallet))
            bar()

    print()
    return chains


def get_wallet_balance(node_process, session, address):
    payload = {
        'user_addr': address,
    }
    edit_session_headers(node_process, session, payload, 'GET', '/asset/net_curve_24h')

    resp = send_request(
        node_process,
        session=session,
        method='GET',
        url=f'https://api.debank.com/asset/net_curve_24h?user_addr={address}',
    )

    usd_value = resp.json()['data']['usd_value_list'][-1][1]

    return usd_value


def get_pools(node_process, session, wallets):
    def get_pool(session, address):
        pools = {}
        payload = {
            'user_addr': address,
        }
        edit_session_headers(node_process, session, payload, 'GET', '/portfolio/project_list')

        resp = send_request(
            node_process,
            session=session,
            method='GET',
            url=f'https://api.debank.com/portfolio/project_list?user_addr={address}',
        )

        for pool in resp.json()['data']:
            pools[f"{pool['name']} ({pool['chain']})"] = []
            for item in pool['portfolio_item_list']:
                for coin in item['asset_token_list']:
                    pools[f"{pool['name']} ({pool['chain']})"].append({
                        'amount': coin['amount'],
                        'name': coin['name'],
                        'ticker': coin['optimized_symbol'],
                        'price': coin['price'],
                        'logo_url': coin['logo_url']
                    })

        return pools
    
    all_pools = {}

    with alive_bar(len(wallets)) as bar:
        for wallet in wallets:
            pools = get_pool(session, wallet)
            for pool in pools:
                if (pool not in all_pools):
                    all_pools[pool] = {}
                all_pools[pool][wallet] = pools[pool]
            bar()

    for pool in all_pools:
        for wallet in wallets:
            if (wallet not in all_pools[pool]):
                all_pools[pool][wallet] = []
    print()

    return all_pools


def worker(queue_tasks, queue_results):
    session, node_process = setup_session()

    while True:
        task = queue_tasks.get()
        if (task[0] == 'chain_balance'):
            balance = chain_balance(node_process, session, task[1], task[2], task[3], task[4])
            queue_results.put((task[2], task[1], balance))
        elif (task[0] == 'get_wallet_balance'):
            balance = get_wallet_balance(node_process, session, task[1])
            queue_results.put((task[1], balance))
        elif (task[0] == 'done'):
            queue_tasks.put(('done',))
            break


def get_balances(wallets, ticker=None):
    session, node_process = setup_session()

    logger.info('Получение списка использованных на кошельках сетей...')
    chains = list(get_chains(node_process, session, wallets))
    logger.info('Получение списка пулов и баланса кошельков в них...')
    pools = get_pools(node_process, session, wallets)
    logger.success(f'Готово! Всего сетей и пулов: {len(chains) + len(pools)}\n')

    min_amount = get_minimal_amount_in_usd()
    num_of_threads = get_num_of_threads()
    selected_chains = select_chains(chains + [pool for pool in pools])

    coins = {chain: dict() for chain in selected_chains}
    coins.update(pools)
    pools_names = [pool for pool in pools]


    queue_tasks = Queue()
    queue_results = Queue()

    threads = []
    for _ in range(num_of_threads):
        th = threading.Thread(target=worker, args=(queue_tasks, queue_results))
        threads.append(th)
        th.start()

    start_time = time()
    for chain_id, chain in enumerate(selected_chains):
        if (chain not in pools_names):
            logger.info(f'[{chain_id + 1}/{len(selected_chains) - len(set(selected_chains) & set(pools_names))}] Получение баланса в сети {chain.upper()}...')

            for wallet in wallets:
                queue_tasks.put(('chain_balance', wallet, chain, ticker, min_amount))

            with alive_bar(len(wallets)) as bar:
                for wallet in wallets:
                    result = queue_results.get()
                    coins[result[0]][result[1]] = result[2]
                    bar()

    print()
    logger.info('Получение баланса во всех сетях для каждого кошелька')
    for wallet in wallets:
        queue_tasks.put(('get_wallet_balance', wallet))

    balances = {}
    with alive_bar(len(wallets)) as bar:
        for wallet in wallets:
            result = queue_results.get()
            balances[result[0]] = result[1]
            bar()

    queue_tasks.put(('done',))
    for th in threads:
        th.join()

    if (ticker is None):
        save_full_to_excel(wallets, selected_chains, coins, balances)
    else:
        save_selected_to_excel(wallets, selected_chains, coins, balances, ticker)

    print()
    logger.success(f'Готово! Таблица сохранена в {file_excel}')
    logger.info(f'Затрачено времени: {round((time() - start_time) / 60, 1)} мин.\n')


def main():
    art = text2art(text="DEBANK   CHECKER", font="standart")
    print(colored(art,'light_blue'))
    print(colored('Автор: t.me/cryptogovnozavod\n','light_cyan'))

    with open(file_wallets, 'r') as file:
        wallets = [row.strip().lower() for row in file]

    logger.success(f'Успешно загружено {len(wallets)} адресов\n')

    while True:
        action = get_action()

        match action:
            case 'Получить балансы для всех токенов на кошельках':
                get_balances(wallets)
            case 'Получить баланс только конкретного токена':
                ticker = get_ticker()
                get_balances(wallets, ticker)
            case 'Справка':
                show_help()
            case 'Выход':
                exit()
            case _:
                pass


if (__name__ == '__main__'):
    main()
