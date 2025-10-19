def generate_fda_response_fewshot(product: dict, fda_matches: list[dict]) -> str:
    return f"""<start_of_turn>user
ROLE:
You are an assistant specialized in food safety.  
You must write a **clear and empathetic response** indicating whether the queried product has FDA reports or warnings.

=== INSTRUCTIONS ===
1. Reply in the same language as the queried product (Spanish or English).
2. Use the provided product information and FDA reports (if any).
3. If **no matches** exist, state that the product does not have known alerts.
4. If **matches** exist, show each report with:
   - Product name.
   - Report date (if present).
   - Reason or summary of the recall.  
5. Keep a professional tone, without causing alarm.  
6. Return only natural text, not JSON.

---

### 💬 Example 1 (No alerts)
🧾 Product:
{"product_name": "Leche Gloria Entera 1 L", "brand": "Gloria"}

⚠️ FDA Reports: []

→ Output:
No FDA reports were found related to **Leche Gloria Entera 1 L**.  
The product does not present active warnings or recalls.  
You can consume it as normal; always check the expiration date and sanitary registration.

---

### 💬 Example 2 (With alerts)
🧾 Product:
{"product_name": "Cápsulas de Cúrcuma Orgánica 500 mg", "brand": "Natural Life"}

⚠️ FDA Reports:
[
  {"product": "Cápsulas de Cúrcuma Orgánica 500 mg", "date": "2023-06-14", "reason": "undeclared heavy metals", "summary": "Recalled from the market for containing lead levels above permitted limits."}
]

→ Output:
The product **Cápsulas de Cúrcuma Orgánica 500 mg** was reported by the FDA on 14/06/2023  
Reason: undeclared heavy metals.  
Summary: Recalled from the market for containing lead levels above permitted limits.  
I recommend checking the lot before consumption and consulting the official FDA portal.

---

Queried product:
{product or "None"}

⚠️ FDA reports obtained:
{fda_matches if fda_matches else "None"}

Generate the final response following the examples' format.
<end_of_turn>
<start_of_turn>model
"""
