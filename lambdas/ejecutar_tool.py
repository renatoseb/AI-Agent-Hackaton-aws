from lambdas.tools import *
from db.messages import insert_message
import json
import time


def ejecutar_tool(response, intention, messages_log=None, conn=None, session_id=None, processor = None):
    """
    Recibe la respuesta del selector de tools (formato internal) y opcionalmente el messages_log.
    Extrae el TOOL y Thought, registra eventos en messages_log, y ejecuta la función correspondiente.
    """
    try:
        # Guardar raw response (as log)
        if messages_log is not None:
            ev = {"ts": int(time.time() * 1000), "type": "log", "content": {"event": "received_tool_response", "response": response}, "meta": {}}
            messages_log.append(ev)
            if conn is not None and session_id is not None:
                try:
                    insert_message(conn, session_id, ev["ts"], ev["type"], ev["content"], ev["meta"])
                except Exception:
                    pass
        # Extrae la sección relevante
        content = None
        if isinstance(response, dict):
            # expected format from format_tool_selection_prompt: {"content":[{"text": <dict>, "type":"text"}], ...}
            try:
                content = response["content"][0]["text"]
            except Exception:
                content = response.get("content")
        else:
            content = response

        # content should be a dict like {"TOOL": "Consultar_Deuda", "Thought": "..."}
        tool_name = None
        thought = None
        if isinstance(content, dict):
            tool_name = content.get("TOOL")
            thought = content.get("Thought")

        if thought:
            print(f"🧠 Thought del modelo: {thought}")
            if messages_log is not None:
                ev = {"ts": int(time.time() * 1000), "type": "llm_thought", "content": thought, "meta": {}}
                messages_log.append(ev)
                if conn is not None and session_id is not None:
                    try:
                        insert_message(conn, session_id, ev["ts"], ev["type"], ev["content"], ev["meta"])
                    except Exception:
                        pass
        if not tool_name:
            print("⚠️ No se encontró TOOL en la respuesta.")
            return {"error": "no_tool_found", "raw": content}

        print(f"🔧 Llamando a TOOL: {tool_name}")
        if messages_log is not None:
            ev = {"ts": int(time.time() * 1000), "type": "tool_called", "content": tool_name, "meta": {}}
            messages_log.append(ev)
            if conn is not None and session_id is not None:
                try:
                    insert_message(conn, session_id, ev["ts"], ev["type"], ev["content"], ev["meta"])
                except Exception:
                    pass

    # Resolve function name to actual callable
        func = globals().get(tool_name)
        if func is None:
            print(f"⚠️ La función '{tool_name}' no está definida en este módulo.")
            # try importing from lambdas dynamically
            try:
                module = __import__(f"lambdas.{tool_name}.{tool_name}", fromlist=[tool_name])
                func = getattr(module, tool_name)
            except Exception:
                func = None

        if func is None:
            return {"error": "tool_not_found", "tool": tool_name}

        # Prepare input_data for the tool. If processor is available, ask the model to extract a JSON with variables
        input_data = {}
        # If the response contains more structured content, merge it
        if isinstance(response, dict):
            # if the model returned the parsed json already, include it
            try:
                parsed = response.get("content", [])[0].get("text")
                if isinstance(parsed, dict):
                    input_data.update(parsed)
            except Exception:
                pass

        # If we have an intention string and a processor, ask the model to extract parameters as JSON
        if processor is not None and isinstance(intention, str):
            extractor_prompt = (
                "Extrae en JSON los parámetros relevantes de la siguiente intención. "
                "Devuelve únicamente un objeto JSON.\n\nINTENTION:\n" + intention + "\n\n" +
                "Si no hay parámetros devuelve {}."
            )
            try:
                extracted = processor.process_request(extractor_prompt)
                # try to parse JSON from the model
                try:
                    parsed = json.loads(extracted)
                    if isinstance(parsed, dict):
                        input_data.update(parsed)
                except Exception:
                    # ignore parse error; pass raw extracted as 'extracted_text'
                    input_data.setdefault("extracted_text", extracted)
            except Exception:
                pass

        # Ejecuta la función y captura su resultado
        try:
            # Prefer calling with signature (input_data, intention, processor, conn, session_id)
            result = func(input_data, intention, processor, conn, session_id)
        except TypeError:
            # try more legacy signatures
            try:
                result = func(input_data)
            except Exception as e:
                try:
                    result = func()
                except Exception as e2:
                    result = {"error": "tool_execution_failed", "exc": str(e2)}

        # persist tool_result to messages_log and DB
        if messages_log is not None:
            ev = {"ts": int(time.time() * 1000), "type": "tool_result", "content": result, "meta": {"tool": tool_name}}
            messages_log.append(ev)
            if conn is not None and session_id is not None:
                try:
                    insert_message(conn, session_id, ev["ts"], ev["type"], ev["content"], ev["meta"])
                except Exception:
                    pass

        return {"tool": tool_name, "result": result}

    except Exception as e:
        print("❌ Error al ejecutar TOOL:", e)
        return {"error": "exception", "exc": str(e)}