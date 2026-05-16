import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent / "data.db"

def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = connect()
    c = conn.cursor()
    c.execute('''
    CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY,
        name TEXT,
        email TEXT,
        phone TEXT,
        message TEXT,
        created_at TEXT
    )
    ''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS chats (
        id INTEGER PRIMARY KEY,
        user_name TEXT,
        question TEXT,
        answer TEXT,
        created_at TEXT
    )
    ''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS faqs (
        id INTEGER PRIMARY KEY,
        question TEXT,
        answer TEXT
    )
    ''')
    conn.commit()
    conn.close()

def save_lead(name, email, phone, message):
    conn = connect()
    c = conn.cursor()
    c.execute("INSERT INTO leads (name,email,phone,message,created_at) VALUES (?,?,?,?,?)",
              (name, email, phone, message, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def save_chat(user_name, question, answer):
    conn = connect()
    c = conn.cursor()
    c.execute("INSERT INTO chats (user_name,question,answer,created_at) VALUES (?,?,?,?)",
              (user_name, question, answer, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def add_faq(question, answer):
    conn = connect()
    c = conn.cursor()
    c.execute("INSERT INTO faqs (question,answer) VALUES (?,?)", (question, answer))
    conn.commit()
    conn.close()

def get_faqs():
    conn = connect()
    c = conn.cursor()
    c.execute("SELECT * FROM faqs")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def find_faq(query):
    # simple keyword match fallback
    q = query.lower()
    for row in get_faqs():
        if row['question'] and row['question'].lower() in q:
            return row['answer']
    # look for keyword overlap
    for row in get_faqs():
        for tok in row['question'].lower().split():
            if tok in q:
                return row['answer']
    return None
