import mysql.connector
from config import DB_CONFIG

def get_connection():
    return mysql.connector.connect(**DB_CONFIG)

def save_chat(q, a):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_query TEXT,
            bot_response TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        cursor.execute(
            "INSERT INTO chats (user_query, bot_response) VALUES (%s, %s)",
            (q, a)
        )

        conn.commit()

    except Exception as e:
        print("DB ERROR:", e)

    finally:
        try:
            cursor.close()
            conn.close()
        except:
            pass