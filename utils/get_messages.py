"""Obtener historial de mensajes para una session_id.

Busca primero en Postgres (env PGMESSAGES_DSN o DATABASE_URL) en tabla messages; si no, busca en SQLite messages.db.

Input: {"session_id": "...", "limit": 100}
Output: {"messages": [...]} with each row as dict
"""
import os
from typing import Dict, Any

def Get_Messages(input_data: Dict[str, Any] = None):
    input_data = input_data or {}
    session_id = input_data.get("session_id")
    limit = int(input_data.get("limit", 100))
    pg_dsn = os.environ.get("PGMESSAGES_DSN") or os.environ.get("DATABASE_URL")
    if pg_dsn:
        try:
            import psycopg2
            import psycopg2.extras
            conn = psycopg2.connect(pg_dsn)
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            if session_id:
                cur.execute("SELECT session_id, ts, type, content, meta FROM messages WHERE session_id = %s ORDER BY ts ASC LIMIT %s", (session_id, limit))
            else:
                cur.execute("SELECT session_id, ts, type, content, meta FROM messages ORDER BY ts ASC LIMIT %s", (limit,))
            rows = cur.fetchall()
            cur.close()
            conn.close()
            return {"messages": [dict(r) for r in rows]}
        except Exception as e:
            return {"error": "pg_error", "exc": str(e)}

    # SQLite fallback
    try:
        import sqlite3, json
        conn = sqlite3.connect("messages.db")
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        if session_id:
            cur.execute("SELECT session_id, ts, type, content, meta FROM messages WHERE session_id = ? ORDER BY ts ASC LIMIT ?", (session_id, limit))
        else:
            cur.execute("SELECT session_id, ts, type, content, meta FROM messages ORDER BY ts ASC LIMIT ?", (limit,))
        rows = cur.fetchall()
        out = []
        for r in rows:
            d = dict(r)
            try:
                d['content'] = json.loads(d['content']) if d.get('content') else None
            except Exception:
                pass
            try:
                d['meta'] = json.loads(d['meta']) if d.get('meta') else None
            except Exception:
                pass
            out.append(d)
        cur.close()
        conn.close()
        return {"messages": out}
    except Exception as e:
        return {"error": "sqlite_error", "exc": str(e)}


if __name__ == "__main__":
    print(Get_Messages({"session_id": "test-session-1", "limit": 10}))
