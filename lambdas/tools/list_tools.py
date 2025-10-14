"""Listar herramientas desde Postgres.

Input: optional {"limit": 50}
Output: {"tools": [...]}
"""
import os
from typing import Dict, Any

def List_Tools(input_data: Dict[str, Any] = None, intention: str = None, processor=None, conn=None, session_id=None):
    input_data = input_data or {}
    limit = int(input_data.get("limit", 50))

    if processor and intention and not input_data.get("limit"):
        try:
            prompt = "Extrae en JSON {'limit': <n>} desde la intención:\n" + intention
            out = processor.process_request(prompt)
            import json
            try:
                parsed = json.loads(out)
                limit = int(parsed.get("limit", limit))
            except Exception:
                pass
        except Exception:
            pass
    pg_dsn = os.environ.get("PGTOOLS_DSN") or os.environ.get("DATABASE_URL")
    if pg_dsn:
        try:
            import psycopg2
            import psycopg2.extras
            conn = psycopg2.connect(pg_dsn)
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("SELECT name, description FROM tools LIMIT %s", (limit,))
            rows = cur.fetchall()
            cur.close()
            conn.close()
            return {"tools": rows}
        except Exception as e:
            return {"error": "pg_error", "exc": str(e)}
    # fallback simulated
    return {"tools": [{"name": "Consultar_Deuda", "description": "Consultar deuda del usuario"}]}


if __name__ == "__main__":
    print(List_Tools({"limit": 5}))
