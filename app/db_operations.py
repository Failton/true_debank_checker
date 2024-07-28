import sqlite3
from contextlib import closing

def get_db_connection(db_file):
    return sqlite3.connect(db_file)

def save_to_database(db_file, wallets, chains, coins, balances, pools):
    with closing(get_db_connection(db_file)) as conn:
        with conn:
            cursor = conn.cursor()
            
            # Create a new import run
            cursor.execute("INSERT INTO import_run DEFAULT VALUES")
            import_run_id = cursor.lastrowid

            # Insert wallets
            cursor.executemany("INSERT OR IGNORE INTO wallet (address) VALUES (?)",
                               [(wallet,) for wallet in wallets])

            # Insert chains
            cursor.executemany("INSERT OR IGNORE INTO chain (name) VALUES (?)",
                               [(chain,) for chain in chains])

            # Prepare token lookup
            cursor.execute("SELECT id, name FROM token")
            token_lookup = {name: id for id, name in cursor.fetchall()}

            # Insert tokens and wallet_tokens
            for chain in coins:
                chain_id = cursor.execute("SELECT id FROM chain WHERE name = ?", (chain,)).fetchone()[0]
                for wallet, tokens in coins[chain].items():
                    wallet_id = cursor.execute("SELECT id FROM wallet WHERE address = ?", (wallet,)).fetchone()[0]
                    for token in tokens:
                        if token['name'] not in token_lookup:
                            cursor.execute("INSERT INTO token (name) VALUES (?)", (token['name'],))
                            token_lookup[token['name']] = cursor.lastrowid
                        token_id = token_lookup[token['name']]

                        cursor.execute("""
                            INSERT INTO wallet_token (import_run_id, token_id, wallet_id, chain_id, quantity, token_price, value)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (import_run_id, token_id, wallet_id, chain_id, token['amount'], token['price'], token['amount'] * token['price']))

            # Prepare protocol lookup
            cursor.execute("SELECT id, name FROM protocol")
            protocol_lookup = {name: id for id, name in cursor.fetchall()}

            # Insert protocols and pools
            for pool_name, pool_data in pools.items():
                protocol_name, chain_name = pool_name.rsplit(' ', 1)
                chain_name = chain_name.strip('()')

                if protocol_name not in protocol_lookup:
                    cursor.execute("INSERT INTO protocol (name) VALUES (?)", (protocol_name,))
                    protocol_lookup[protocol_name] = cursor.lastrowid
                protocol_id = protocol_lookup[protocol_name]

                chain_id = cursor.execute("SELECT id FROM chain WHERE name = ?", (chain_name,)).fetchone()[0]

                for wallet, tokens in pool_data.items():
                    wallet_id = cursor.execute("SELECT id FROM wallet WHERE address = ?", (wallet,)).fetchone()[0]
                    for token in tokens:
                        if token['name'] not in token_lookup:
                            cursor.execute("INSERT INTO token (name) VALUES (?)", (token['name'],))
                            token_lookup[token['name']] = cursor.lastrowid
                        token_id = token_lookup[token['name']]

                        cursor.execute("""
                            INSERT INTO pool (import_run_id, token_id, wallet_id, chain_id, protocol_id, quantity, token_price, value)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (import_run_id, token_id, wallet_id, chain_id, protocol_id, token['amount'], token['price'], token['amount'] * token['price']))
