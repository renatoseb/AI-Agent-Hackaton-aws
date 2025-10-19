"""Sugerir recetas a partir de una lista de ingredientes.

Input: {"ingredients": ["tomate", "ajo"], "limit": 5}
Output: {"results": [{...}], "missing": [...]}

Comprueba ingredientes contra la colección `fda` para advertencias.
"""
import os
from typing import Dict, Any, List
from prompts.extract_ingredients import extract_ingredients_query_fewshot 
from prompts.recipe_response_format_en import format_results_with_warnings_fewshot


def Recomendar_Ingredientes(intention: str = None, processor=None, conn=None, session_id=None):
    ingredients = []
    limit = 5

    # Try to extract ingredients from intention using processor if not provided
    if (not ingredients or len(ingredients) == 0) and intention:
        # First try deterministic normalization for search
        try:
            norm = extract_ingredients_query_fewshot(intention)
            # normalize_for_recipe_search returns a prompt; the processor would normally be used to run it,
            # but the function itself formats the search phrase in the end. We'll try to run the prompt
            # through processor if available to get a refined extraction; otherwise fall back to simple split.
            if processor:
                out = processor.process_request(norm)
                import json
                try:
                    parsed = json.loads(out)
                    ingredients = parsed.get("ingredients", ingredients)
                    limit = int(parsed.get("limit", limit))
                except Exception:
                    # If model returns plain text, split into words
                    ingredients = [s.strip() for s in out.split(",") if s.strip()]
            else:
                # Fallback: take keywords from the normalized phrase
                # The normalize prompt expects the model to return a short query; extract last line
                try:
                    # call the helper directly to obtain a short query (without running model)
                    short_q = extract_ingredients_query_fewshot(intention).splitlines()[-3] if isinstance(extract_ingredients_query_fewshot(intention), str) else ""
                    # fallback split
                    ingredients = [s.strip() for s in short_q.split() if s.strip()][:6]
                except Exception:
                    ingredients = [s.strip() for s in intention.split(",") if s.strip()]
        except Exception:
            ingredients = [s.strip() for s in intention.split(",") if s.strip()]
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
            query = {"$text": {"$search": ingredients}} if ingredients else {}
            docs = list(col_recetas.find(query, {"_id": 0}).limit(limit))

            # Revisar si alguno de los ingredientes aparece en FDA como riesgo
            for ing in ingredients:
                query_fda = {"$text": {"$search": ing}}
                hit = col_fda.find_one(query_fda, {"_id": 0}).limit(1)
                if hit:
                    warnings.append({"ingredient": ing, "fda": hit})

            # If we have a processor, format a conversational textual response using the recipe_response_format prompt
            if processor:
                try:
                    prompt = format_results_with_warnings_fewshot(intention, docs, warnings)
                    text = processor.process_request(prompt)
                    return {"text": text}
                except Exception:
                    pass

            # Fallback: return raw results if processor is not available or fails
            return {"results": docs, "warnings": warnings}
        except Exception as e:
            return {"error": "mongo_error", "exc": str(e)}

    # Fallback simulated
    return {"results": [{"title": "Ensalada simple", "ingredients": ingredients}], "warnings": []}


if __name__ == "__main__":
    print(Recomendar_Ingredientes({"ingredients": ["tomate","lechuga"]}))
