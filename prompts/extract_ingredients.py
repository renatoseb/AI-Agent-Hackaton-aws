def extract_ingredients_query_fewshot(intention: str) -> str:
    return f"""<start_of_turn>user
ROLE:
You are a culinary information extractor.  
Your task is to read the user's message and identify which **ingredients** they mention and how many recipe results they would like to see.

=== INSTRUCTIONS ===
1. Analyze the user's intention and extract a clean list of ingredients (only food items, no adjectives or verbs).  
2. If the user mentions a desired number of recipes (e.g., "show me 3 ideas"), capture it as `"limit"`.  
3. If no number is given, set `"limit": 5` by default.  
4. Return a **valid JSON** object with two keys:
   - `"ingredients"` → array of ingredient names in lowercase English.
   - `"limit"` → integer number of recipes to retrieve.
5. Do **not** add explanations, commentary, or text outside the JSON.

---

### 💬 FEW-SHOT EXAMPLES

USER: "Show me some recipes with tomato and garlic"  
OUTPUT:
{{"ingredients": ["tomato", "garlic"], "limit": 5}}

USER: "I'd like 3 ideas using chicken, rice and beans"
OUTPUT:
{{"ingredients": ["chicken", "rice", "beans"], "limit": 3}}

USER: "Suggest healthy meals with spinach and avocado"
OUTPUT:
{{"ingredients": ["spinach", "avocado"], "limit": 5}}

USER: "Give me 10 recipes that include salmon and lemon"
OUTPUT:
{{"ingredients": ["salmon", "lemon"], "limit": 10}}

USER MESSAGE:
{intention}

Return only the JSON.
<end_of_turn>
<start_of_turn>model
"""