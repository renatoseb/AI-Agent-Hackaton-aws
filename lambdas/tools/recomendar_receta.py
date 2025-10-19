"""Buscar receta por nombre o ingrediente.

Usage:
  - Input: dict con keys opcionales: {"q": "nombre o ingrediente", "limit": 5}
  - Output: dict {"hits": [...]} donde cada hit es el documento de receta reducido.

Conexión: usa MONGO_URI env var si está disponible; si no, devuelve simulación.
"""
import os
import json
from typing import Dict, Any
from prompts.recipe_extraction_en import normalize_for_recipe_search
from prompts.recipe_response_format_en import format_results_with_warnings_fewshot


def Recomendar_Receta(intention: str = None, processor=None, conn=None, session_id=None):
    """Ahora acepta (input_data, intention, processor, conn, session_id).
    Si `processor` está presente y `intention` tiene texto, intentará extraer 'q' y 'limit' mediante el modelo.
    """
    q = None
    limit = 5

    # If we have no q but intention, try to normalize intention into a short query
    if not q and intention:
        try:
            norm_prompt = normalize_for_recipe_search(intention)
            if processor:
                out = processor.process_request(norm_prompt)
                print('Processor output:', out)
                # model might return a short query or JSON; try to parse
                try:
                    parsed = json.loads(out)
                    q = q or parsed.get("q")
                    limit = int(parsed.get("limit", limit))
                except Exception:
                    q = q or out.strip()
            else:
                # fallback: use the cleaned intention tokens
                q = q or intention
        except Exception:
            q = q or intention

    mongo_uri = os.environ.get("MONGO_URI")
    print('Mongo URI:', mongo_uri)

    if mongo_uri:
        try:
            from pymongo import MongoClient
            client = MongoClient(mongo_uri)
            db = client['off']
            col = db.get_collection("recetas")
            # Buscar por nombre o ingrediente (simple text search)
            # Use MongoDB text index for basic relevance/similarity (create text index on product_name and ingredients)
            # Note: this is better than regex for relevance. For semantic similarity use embeddings or Atlas Search.
            query = {"$text": {"$search": q}} if q else {}
            docs = list(col.find(query, {"_id": 0}).limit(limit))

            # If processor is available, format a text response using recipe_response_format
            if processor:
                try:
                    prompt = format_results_with_warnings_fewshot(intention, docs, [])
                    text = processor.process_request(prompt)
                    return {"text": text}
                except Exception:
                    print("⚠️ Warning: failed to format results with processor.")

            return {"hits": docs}
        except Exception as e:
            return {"error": "mongo_error", "exc": str(e)}
    # Fallback: simulated response
    sample = [{"title": "Tortilla de patatas", "ingredients": ["huevos", "patatas", "cebolla"], "steps": ["pelar", "freir", "batir"]}]
    return {"hits": sample[:limit]}


if __name__ == "__main__":
    print(Recomendar_Receta({"q": "huevos", "limit": 2}))
