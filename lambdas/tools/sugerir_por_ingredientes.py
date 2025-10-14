"""Sugerir recetas a partir de una lista de ingredientes.

Input: {"ingredients": ["tomate", "ajo"], "limit": 5}
Output: {"results": [{...}], "missing": [...]}

Comprueba ingredientes contra la colección `fda` para advertencias.
"""
import os
from typing import Dict, Any, List

def Sugerir_Por_Ingredientes(input_data: Dict[str, Any] = None, intention: str = None, processor=None, conn=None, session_id=None):
    input_data = input_data or {}
    ingredients = input_data.get("ingredients", [])
    limit = int(input_data.get("limit", 5))

    # Try to extract ingredients from intention using processor if not provided
    if (not ingredients or len(ingredients) == 0) and processor and intention:
        try:
            prompt = "Extrae en JSON {'ingredients': [..], 'limit': <n>} desde la intención:\n" + intention
            out = processor.process_request(prompt)
            import json
            try:
                parsed = json.loads(out)
                ingredients = parsed.get("ingredients", ingredients)
                limit = int(parsed.get("limit", limit))
            except Exception:
                # fallback: split intention by commas
                ingredients = [s.strip() for s in intention.split(",") if s.strip()]
        except Exception:
            pass
    mongo_uri = os.environ.get("MONGO_URI")
    results = []
    warnings = []
    if mongo_uri:
        try:
            from pymongo import MongoClient
            client = MongoClient(mongo_uri)
            db = client.get_default_database()
            col_recetas = db.get_collection("recetas")
            col_fda = db.get_collection("fda")

            # Buscar recetas que contengan la mayoría de los ingredientes
            regexes = [ {"ingredients": {"$regex": ing, "$options": "i"}} for ing in ingredients ]
            docs = list(col_recetas.find({"$and": regexes}, {"_id": 0}).limit(limit))

            # Revisar si alguno de los ingredientes aparece en FDA como riesgo
            for ing in ingredients:
                hit = col_fda.find_one({"product_name": {"$regex": ing, "$options": "i"}}, {"_id": 0})
                if hit:
                    warnings.append({"ingredient": ing, "fda": hit})

            return {"results": docs, "warnings": warnings}
        except Exception as e:
            return {"error": "mongo_error", "exc": str(e)}

    # Fallback simulated
    return {"results": [{"title": "Ensalada simple", "ingredients": ingredients}], "warnings": []}


if __name__ == "__main__":
    print(Sugerir_Por_Ingredientes({"ingredients": ["tomate","lechuga"]}))
