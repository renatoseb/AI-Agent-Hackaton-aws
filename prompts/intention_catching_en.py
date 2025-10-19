def catch_intention(chat_history: str) -> str:
    return """<start_of_turn>user
ROLE:
You are a conversation analyst.  
Your task is to analyze the full message history between a user and the virtual assistant to **summarize the user's current intention in a single clear and concise sentence**.

---

=== INSTRUCTIONS ===
1. Reply in the same language as the history.
2. You will be given a JSON list under the key `"messages"` with the format:
   [
     { "role": "user", "content": [...] },
     { "role": "assistant", "content": [...] },
     ...
   ]

3. The messages are **ordered from oldest to most recent**.

4. Read the most recent content to understand what the user wants at the end of the conversation, but use earlier context to avoid misinterpretations.

5. Your output **must be exclusively a single line of text** that summarizes the user's current intention, without explanations, without JSON or additional formatting.

6. Examples:
   - If the history ends with “🧾 Estado de cuenta” → output: `El usuario quiere consultar su estado de cuenta o deuda actual.`
   - If it ends with “Quiero mi boleta” → output: `User wants to obtain their payment receipt or slip.`
   - If it ends with “Pago” and earlier it discussed payment methods → output: `El usuario busca información sobre los medios disponibles para pagar.`

7. Do not include the tokens `<eos>` or `<end_of_turn>` in the output.

---

=== MESSAGE HISTORY ===
""" + chat_history + """
---

Reply only with the **final summary sentence**, nothing else.
<end_of_turn>
<start_of_turn>model
"""
