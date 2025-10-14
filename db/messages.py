import json


def create_messages_table(conn):
    with conn.cursor() as cur:
        cur.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id SERIAL PRIMARY KEY,
                session_id VARCHAR(100) NOT NULL,
                ts BIGINT NOT NULL,
                type VARCHAR(50) NOT NULL,
                content JSONB,
                meta JSONB
            );
        ''')
        conn.commit()


def insert_message(conn, session_id, ts, type_, content, meta=None):
    # content and meta will be stored as JSONB; convert to JSON string if needed
    content_json = None
    meta_json = None
    try:
        content_json = json.dumps(content, ensure_ascii=False) if content is not None else None
    except Exception:
        # fallback to string representation
        content_json = json.dumps({"text": str(content)}, ensure_ascii=False)

    try:
        meta_json = json.dumps(meta, ensure_ascii=False) if meta is not None else None
    except Exception:
        meta_json = json.dumps({"meta": str(meta)}, ensure_ascii=False)

    with conn.cursor() as cur:
        cur.execute('''
            INSERT INTO messages (session_id, ts, type, content, meta)
            VALUES (%s, %s, %s, %s::jsonb, %s::jsonb)
        ''', (session_id, ts, type_, content_json, meta_json))
        conn.commit()
