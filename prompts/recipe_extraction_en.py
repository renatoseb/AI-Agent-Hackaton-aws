def normalize_for_recipe_search(intention: str) -> str:
    return f"""<start_of_turn>user
ROLE:
You are an assistant specialized in semantic retrieval of cooking recipes.  
Your task is to convert the user's intention into a **short and precise search query**, optimized to find relevant recipes in a database.

=== INSTRUCTIONS ===
1. Reply in the same language as the intention.
2. Analyze the received intention.
3. Identify ingredients, dish type, restrictions or preferences (e.g. healthy, low-fat, dessert, vegan, Peruvian, etc.).
4. Reformulate the intention as a single **short phrase** or **list of key terms** for similarity search.
5. Do not include explanations, JSON, or additional formatting.  
6. Always use neutral language, without emojis or extra characters.

Examples:
- Intention: "El usuario quiere una receta saludable con papa amarilla."  
  → Output: "receta saludable con papa amarilla"
- Intention: "El usuario busca ideas de almuerzos bajos en carbohidratos."  
  → Output: "recetas bajas en carbohidratos para almuerzo"
- Intention: "El usuario desea postres sin azúcar ni gluten."  
  → Output: "recetas de postres sin azúcar ni gluten"

---

INTENTION:
{intention}
---

Reply only with the final query ready for use in search.
<end_of_turn>
<start_of_turn>model
"""
