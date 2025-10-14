"""Comprobar un producto por nombre/gtin en collections de Mongo: products_with_ingredients_no_petfood y fda.

Input: {"q": "nombre o gtin"}
Output: {"product": {...}, "fda_matches": [...]}
"""
import os
from typing import Dict, Any

def Check_Producto(input_data: Dict[str, Any] = None, intention: str = None, processor=None, conn=None, session_id=None):
    input_data = input_data or {}
    q = input_data.get("q", "")

    if not q and processor and intention:
        try:
            prompt = "Extrae en JSON {'q': <query>} desde la intención:\n" + intention
            out = processor.process_request(prompt)
            import json
            try:
                parsed = json.loads(out)
                q = parsed.get("q", q)
            except Exception:
                q = q or intention
        except Exception:
            q = q or intention
    mongo_uri = os.environ.get("MONGO_URI")
    if mongo_uri:
        try:
            from pymongo import MongoClient
            client = MongoClient(mongo_uri)
            db = client.get_default_database()
            col_prod = db.get_collection("products_with_ingredients_no_petfood")
            col_fda = db.get_collection("fda")

            prod = col_prod.find_one({"$or": [{"product_name": {"$regex": q, "$options": "i"}}, {"gtin": q}]}, {"_id": 0})
            fda_hits = []
            if prod and "ingredients" in prod:
                # buscar coincidencias FDA por ingrediente o nombre
                for ing in prod.get("ingredients", [])[:10]:
                    hit = list(col_fda.find({"$or": [{"product_name": {"$regex": ing, "$options": "i"}}, {"reason": {"$regex": ing, "$options": "i"}}]}, {"_id": 0}).limit(3))
                    if hit:
                        fda_hits.extend(hit)

            return {"product": prod, "fda_matches": fda_hits}
        except Exception as e:
            return {"error": "mongo_error", "exc": str(e)}
    return {"product": None, "fda_matches": []}


if __name__ == "__main__":
    print(Check_Producto({"q": "leche"}))
