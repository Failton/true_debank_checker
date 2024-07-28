-- Import Run Table
CREATE TABLE import_run (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_date DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Token Table
CREATE TABLE token (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL
);

-- Wallet Table
CREATE TABLE wallet (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    address TEXT NOT NULL UNIQUE
);

-- Chain Table
CREATE TABLE chain (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

-- Protocol Table (New)
CREATE TABLE protocol (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

-- Wallet Token Table
CREATE TABLE wallet_token (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    import_run_id INTEGER NOT NULL,
    token_id INTEGER NOT NULL,
    wallet_id INTEGER NOT NULL,
    chain_id INTEGER NOT NULL,
    quantity FLOAT NOT NULL,
    token_price FLOAT NOT NULL,
    value FLOAT NOT NULL,
    FOREIGN KEY (import_run_id) REFERENCES import_run(id),
    FOREIGN KEY (token_id) REFERENCES token(id),
    FOREIGN KEY (wallet_id) REFERENCES wallet(id),
    FOREIGN KEY (chain_id) REFERENCES chain(id)
);

-- Pool Table (Updated)
CREATE TABLE pool (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    import_run_id INTEGER NOT NULL,
    token_id INTEGER NOT NULL,
    wallet_id INTEGER NOT NULL,
    chain_id INTEGER NOT NULL,
    protocol_id INTEGER NOT NULL,
    quantity FLOAT NOT NULL,
    token_price FLOAT NOT NULL,
    value FLOAT NOT NULL,
    FOREIGN KEY (import_run_id) REFERENCES import_run(id),
    FOREIGN KEY (token_id) REFERENCES token(id),
    FOREIGN KEY (wallet_id) REFERENCES wallet(id),
    FOREIGN KEY (chain_id) REFERENCES chain(id),
    FOREIGN KEY (protocol_id) REFERENCES protocol(id)
);