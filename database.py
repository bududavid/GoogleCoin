import sqlite3

conn = sqlite3.connect('users.db')
cursor = conn.cursor()

conn2 = sqlite3.connect(r'c:\Users\PC\Desktop\AutoViewer\accounts.db')
cursor2 = conn.cursor()

def create_tables():
    # Создание таблиц
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS credentials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        login TEXT,
        password TEXT,
        status TEXT
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        score INTEGER DEFAULT 0,
        created_accounts INTEGER DEFAULT 0
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS temp_check (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        login TEXT,
        password TEXT
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS balances (
        user_id INTEGER PRIMARY KEY,
        balance REAL DEFAULT 0,
        hold_balance REAL DEFAULT 0
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_currency (
        user_id INTEGER PRIMARY KEY,
        currency TEXT DEFAULT 'USD'
    )
    ''')

    # Assuming you have a script to initialize your database
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS referrals (
            user_id INTEGER,
            referrer_id INTEGER,
            earnings REAL DEFAULT 0.0,
            PRIMARY KEY (user_id, referrer_id)
        )
    ''')





    conn.commit()