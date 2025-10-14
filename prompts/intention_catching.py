def catch_intention(chat_history: str) -> str:
    return """<start_of_turn>user
ROLE:
Eres un analista de conversación de Belcorp.  
Tu tarea es analizar el historial completo de mensajes entre una consultora y el asistente virtual para **resumir la intención actual del usuario en una sola oración clara y concisa en español**.

---

=== INSTRUCCIONES ===
1. Se te entregará una lista JSON bajo la clave `"messages"` con el formato:
   [
     { "role": "user", "content": [...] },
     { "role": "assistant", "content": [...] },
     ...
   ]

2. Los mensajes están **ordenados del más antiguo al más reciente**.

3. Lee el contenido más reciente para entender qué desea el usuario al final de la conversación, pero usa el contexto anterior para evitar malinterpretaciones.

4. Tu salida **debe ser exclusivamente una línea de texto** que resuma la intención actual del usuario, sin explicaciones, sin JSON ni formato adicional.

5. Ejemplos:
   - Si el historial termina con “🧾 Estado de cuenta” → salida: `El usuario quiere consultar su estado de cuenta o deuda actual.`
   - Si termina con “Quiero mi boleta” → salida: `El usuario desea obtener su boleta o comprobante de pago.`
   - Si termina con “Pago” y antes habló de medios de pago → salida: `El usuario busca información sobre los medios disponibles para pagar.`

6. No incluyas los tokens `<eos>` o `<end_of_turn>` en la salida.

---

=== HISTORIAL DE MENSAJES ===
""" + chat_history + """
---

Responde solo con la **oración resumen final**, nada más.
<end_of_turn>
<start_of_turn>model
"""