from src.database.db_manager import get_db_connection

DEFAULT_SESSION_NAME = "New conversation"


def list_sessions(user_id):
    """Retourne les sessions de chat de l'utilisateur, les plus récentes en premier."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT session_id, session_name, created_at FROM chat_sessions "
            "WHERE user_id = %s ORDER BY created_at DESC;",
            (user_id,),
        )
        rows = cursor.fetchall()
        cursor.close()
    finally:
        conn.close()
    return [{"session_id": r[0], "session_name": r[1], "created_at": r[2]} for r in rows]


def create_session(user_id, session_name=DEFAULT_SESSION_NAME):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO chat_sessions (user_id, session_name) VALUES (%s, %s) "
            "RETURNING session_id;",
            (user_id, session_name),
        )
        session_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
    finally:
        conn.close()
    return session_id


def rename_session(session_id, session_name):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE chat_sessions SET session_name = %s WHERE session_id = %s;",
            (session_name, session_id),
        )
        conn.commit()
        cursor.close()
    finally:
        conn.close()


def delete_session(session_id):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM chat_sessions WHERE session_id = %s;", (session_id,))
        conn.commit()
        cursor.close()
    finally:
        conn.close()


def load_messages(session_id):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT role, content FROM chat_messages "
            "WHERE session_id = %s ORDER BY message_id ASC;",
            (session_id,),
        )
        rows = cursor.fetchall()
        cursor.close()
    finally:
        conn.close()
    return [{"role": r[0], "content": r[1]} for r in rows]


def count_messages(session_id):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM chat_messages WHERE session_id = %s;", (session_id,))
        count = cursor.fetchone()[0]
        cursor.close()
    finally:
        conn.close()
    return count


def append_message(session_id, role, content):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO chat_messages (session_id, role, content) VALUES (%s, %s, %s);",
            (session_id, role, content),
        )
        conn.commit()
        cursor.close()
    finally:
        conn.close()
