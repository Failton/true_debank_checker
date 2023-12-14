import random
import subprocess
import requests
import tls_client
import json

from time import time, sleep
from .config import *



def generate_req_rapams(node_process, payload, method, path):
    _json = json.dumps(payload)

    node_process.stdin.write(f'{_json}|{method}|{path}')
    sleep(NODE_SLEEP_TIME)
    node_process.stdin.flush()
    output_data = node_process.stdout.readline().strip()
    signature = json.loads(output_data)

    return signature

def edit_session_headers(node_process, session, payload, method, path):
    sig = generate_req_rapams(node_process, payload, method, path)
    session.headers['x-api-nonce'] = sig['nonce']
    session.headers['x-api-sign'] = sig['signature']
    session.headers['x-api-ts'] = str(sig['ts'])

    abc = 'abcdef0123456789'
    r_id = ''.join(random.choices(abc, k=32))
    r_time = str(int(time()))
    info = {
        'random_at': r_time,
        'random_id': r_id,
        'user_addr': None
    }
    account = json.dumps(info)
    session.headers['account'] = account


def send_request(node_process, session, method, url, payload={}, params={}):
    while True:
        try:
            if (method == 'GET'):
                resp = session.execute_request(method=method, url=url)
            else:
                resp = session.request(method=method, url=url, json=payload, params=params)

            if (resp.status_code == 200):
                if 'data' in resp.text and resp.json():
                    #logger.info(session.headers['x-api-nonce'])
                    sleep(random.uniform(SLEEP_TIME, SLEEP_TIME+0.05))
                    return resp
                else:
                    logger.error(f'Request not include data | Response: {resp.text}')
            elif (resp.status_code == 429):
                if 'Too Many' in resp.text:
                    #logger.error(f"Too many requests | Headers: {session.headers['x-api-nonce']}")
                    logger.error(f"Too many requests | Headers: {session.headers['x-api-nonce']}")
                    sleep(random.uniform(SLEEP_TIME, SLEEP_TIME+0.05))
                else:
                    logger.error(f'Unknown request error | Response: {resp.text}')
            else:
                logger.error(f'Bad request status code: {resp.status_code} | Method: {method} | Response: {resp.text} | Url: {url} | Headers: {session.headers} | Payload: {payload}')

        except Exception as error:
            logger.error(f'Unexcepted error while sending request to {url}: {error}')

        if (method == 'GET'):
            edit_session_headers(node_process, session, params, method, url.split('api.debank.com')[1].split('?')[0])
        else:
            edit_session_headers(node_process, session, payload, method, url)
        sleep(1)
        

def setup_session():
    session = requests.Session()
    session = tls_client.Session(
        client_identifier="chrome112",
        random_tls_extension_order=True
    )

    headers = {
        'authority': 'api.debank.com',
        'accept': '*/*',
        'accept-language': 'ru-RU,ru;q=0.9',
        'cache-control': 'no-cache',
        'origin': 'https://debank.com',
        'pragma': 'no-cache',
        'referer': 'https://debank.com/',
        'sec-ch-ua': '"Chromium";v="112", "Google Chrome";v="112", "Not:A-Brand";v="99"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Linux"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'source': 'web',
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36',
        'x-api-nonce': 'n_RT2KhwQF08JA3CwiTUOhUnel9ELZPGHDb2UgZLKh',
        'x-api-sign': 'fb69dcdb900a27540c6fd9e13a08db75d16a2b917cfc33991e834552691a1a72',
        'x-api-ts': '1690894427',
        'x-api-ver': 'v2',
    }
    session.headers = headers


    node_process = subprocess.Popen(['node', 'js/main.js'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True)
    return session, node_process
