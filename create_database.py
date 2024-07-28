#!/usr/bin/env python

import sqlite3

def create_database(db_name: str, schema_file: str):
    conn = sqlite3.connect(db_name)
    with open(schema_file, 'r') as f:
        schema = f.read()
    
    conn.executescript(schema)
    conn.commit()
    conn.close()

if __name__ == '__main__':
    db_name = 'db/portfolio_history.db'
    schema_file = 'sql/schema.sql'
    create_database(db_name, schema_file)