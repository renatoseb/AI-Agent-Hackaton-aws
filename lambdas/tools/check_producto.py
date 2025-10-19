"""Comprobar un producto por nombre/gtin en collections de Mongo: products_with_ingredients_no_petfood y fda.

Input: {"q": "nombre o gtin"}
Output: {"product": {...}, "fda_matches": [...]}
"""
import os
from typing import Dict, Any
from prompts.fda_product_extraction_en import extract_fda_query_fewshot
from prompts.fda_resopnse_format_en import generate_fda_response_fewshot

def Check_Producto(intention: str = None, processor=None, conn=None, session_id=None):
    q = None

    # If we have a processor, run the few-shot extractor to get a precise q (product name or GTIN)
    if processor and intention:
        try:
            prompt = extract_fda_query_fewshot(intention)
            out = processor.process_request(prompt)
            import json
            try:
                parsed = json.loads(out)
                q = parsed.get("q") or q
            except Exception:
                q = q or out.strip()
        except Exception:
            pass
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

            # If processor available, format a natural language response
            if processor:
                try:
                    prompt = generate_fda_response_fewshot(prod or {}, fda_hits)
                    text = processor.process_request(prompt)
                    return {"text": text}
                except Exception:
                    pass

            return {"product": prod, "fda_matches": fda_hits}
        except Exception as e:
            return {"error": "mongo_error", "exc": str(e)}
    return {"product": None, "fda_matches": []}


if __name__ == "__main__":
    print(Check_Producto({"q": "leche"}))
