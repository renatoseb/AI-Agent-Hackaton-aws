def extract_fda_query_fewshot(intention: str) -> str:
    return f"""<start_of_turn>user
ROLE:
You are an analyst of food safety queries.  
Your task is to **extract the specific product or GTIN** mentioned in the user's intention, in order to search it in the product and FDA alerts database.

=== INSTRUCTIONS ===
1. Reply in the same language as the intention (Spanish or English).
2. Read the user's intention, which may mention product names, brands or numeric codes.  
3. Return **only a JSON** with the key `"q"` containing the name or code of the main product.  
4. If no clear product is mentioned, return `"q": null`.  
5. Do not include explanations or text outside the JSON.

---

### 💬 Example 1
Intention: "¿La leche Gloria está reportada por la FDA?"  
→ Output: `{"q": "leche Gloria"}`

### 💬 Example 2
Intention: "Consulta el producto 7754561000120"  
→ Output: `{"q": "7754561000120"}`

### 💬 Example 3
Intention: "Hay algún reporte sobre suplementos de cúrcuma?"  
→ Output: `{"q": "suplemento cúrcuma"}`

---

Intention:
{intention}

Reply only with the JSON.
<end_of_turn>
<start_of_turn>model
"""
