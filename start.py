#!/usr/bin/env python3

import threading
import openpyxl
import argparse

from queue import Queue
from time import time

from art import text2art
from alive_progress import alive_bar

from app.excel import *
from app.questions import *
from app.config import *
from app.utils import *
from app.db_operations import *



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
    print('--------------------- HELP ---------------------\n> What does minimum token amount in $ mean?\n> If the token has a dollar amount less than the specified minimum amount, it will not be included in the table\n\n> How to select all networks?\n> When selecting networks, choose the "ALL NETWORKS" option (right arrow) and press enter\n\n> What are worker threads?\n> These are "worker processes" that will simultaneously retrieve information about wallets. The more threads, the higher the chance of getting blocked by Cloudflare. Optimal - 3 threads\n\n> The balance retrieval progress bar is not moving, what should I do?\n> Reduce the number of worker threads / check internet connection\n\n> What\'s the difference between "CHAINS" and "TOTAL" columns?\n> The first is the sum of coins in $ in selected networks and pools, the second is the sum of coins in $ across all networks\n\n> Why is getting the list of networks used on wallets so slow?\n> Because Cloudflare strongly restricts this request, so the work is done in single-thread mode\n\n> Other questions?\n> Write to us in the chat https://t.me/cryptogovnozavod_chat\n--------------------- HELP ---------------------\n')


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


def get_balances(wallets, ticker=None, auto_import=False):
    session, node_process = setup_session()

    logger.info('Getting list of networks used on wallets...')
    chains = list(get_chains(node_process, session, wallets))
    logger.info('Getting list of pools and wallet balances in them...')
    pools = get_pools(node_process, session, wallets)
    logger.success(f'Done! Total networks and pools: {len(chains) + len(pools)}\n')

    if auto_import:
        min_amount = 7
        selected_chains = chains + [pool for pool in pools]
    else:
        min_amount = get_minimal_amount_in_usd()
        selected_chains = select_chains(chains + [pool for pool in pools])

    if auto_import:
        num_of_threads = 1
    else:
        num_of_threads = get_num_of_threads()

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
            logger.info(f'[{chain_id + 1}/{len(selected_chains) - len(set(selected_chains) & set(pools_names))}] Getting balance in network {chain.upper()}...')

            for wallet in wallets:
                queue_tasks.put(('chain_balance', wallet, chain, ticker, min_amount))

            with alive_bar(len(wallets)) as bar:
                for wallet in wallets:
                    result = queue_results.get()
                    coins[result[0]][result[1]] = result[2]
                    bar()

    print()
    logger.info('Getting balance in all networks for each wallet')
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

    # Save output
    if auto_import:
        save_to_database('db/portfolio_history.db', wallets, selected_chains, coins, balances, pools)
        logger.success(f'Done! Data saved to database')
    else:
        if ticker is None:
            save_full_to_excel(wallets, selected_chains, coins, balances)
        else:
            save_selected_to_excel(wallets, selected_chains, coins, balances, ticker)
        print()
        logger.success(f'Done! Table saved in {file_excel}')

    
    logger.info(f'Time taken: {round((time() - start_time) / 60, 1)} min.\n')


def main():
    art = text2art(text="DEBANK   CHECKER", font="standart")
    print(colored(art,'light_blue'))
    print(colored('Author: t.me/cryptogovnozavod\n','light_cyan'))

    with open(file_wallets, 'r') as file:
        wallets = [row.strip().lower() for row in file]

    logger.success(f'Successfully loaded {len(wallets)} addresses\n')

    parser = argparse.ArgumentParser()
    parser.add_argument('--auto-import', action='store_true', help='Run automatic import on all chains')
    args = parser.parse_args()

    if args.auto_import:
        get_balances(wallets, auto_import=True)
    else:
        while True:
            action = get_action()

            match action:
                case 'Get balances for all tokens in wallets':
                    get_balances(wallets)
                case 'Get balance for a specific token only':
                    ticker = get_ticker()
                    get_balances(wallets, ticker)
                case 'Help':
                    show_help()
                case 'Exit':
                    exit()
                case _:
                    pass


if (__name__ == '__main__'):
    main()