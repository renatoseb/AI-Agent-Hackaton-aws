"""Buscar receta por nombre o ingrediente.

Usage:
  - Input: dict con keys opcionales: {"q": "nombre o ingrediente", "limit": 5}
  - Output: dict {"hits": [...]} donde cada hit es el documento de receta reducido.

Conexión: usa MONGO_URI env var si está disponible; si no, devuelve simulación.
"""
import os
import json
from typing import Dict, Any

def Buscar_Receta(input_data: Dict[str, Any] = None, intention: str = None, processor=None, conn=None, session_id=None):
    """Ahora acepta (input_data, intention, processor, conn, session_id).
    Si `processor` está presente y `intention` tiene texto, intentará extraer 'q' y 'limit' mediante el modelo.
    """
    input_data = input_data or {}
    q = input_data.get("q")
    limit = int(input_data.get("limit", 5))

    # If we have no q but intention+processor, try to extract q and limit
    if not q and processor and intention:
        try:
            prompt = "Extrae en JSON {'q': <query text>, 'limit': <num>} desde la intención:\n" + intention
            out = processor.process_request(prompt)
            try:
                parsed = json.loads(out)
                q = q or parsed.get("q")
                limit = int(parsed.get("limit", limit))
            except Exception:
                # fallback: use entire intention as q
                q = q or intention
        except Exception:
            q = q or intention
    mongo_uri = os.environ.get("MONGO_URI")
    if mongo_uri:
        try:
            from pymongo import MongoClient
            client = MongoClient(mongo_uri)
            db = client.get_default_database()
            col = db.get_collection("recetas")
            # Buscar por nombre o ingrediente (simple text search)
            query = {"$or": [{"title": {"$regex": q, "$options": "i"}}, {"ingredients": {"$regex": q, "$options": "i"}}]} if q else {}
            docs = list(col.find(query, {"_id": 0}).limit(limit))
            return {"hits": docs}
        except Exception as e:
            return {"error": "mongo_error", "exc": str(e)}
    # Fallback: simulated response
    sample = [{"title": "Tortilla de patatas", "ingredients": ["huevos", "patatas", "cebolla"], "steps": ["pelar", "freir", "batir"]}]
    return {"hits": sample[:limit]}


if __name__ == "__main__":
    print(Buscar_Receta({"q": "huevos", "limit": 2}))
