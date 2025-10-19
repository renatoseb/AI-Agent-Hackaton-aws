import importlib
import importlib.util
import os
try:
    # attempt to import the package to ensure it's on sys.path
    import lambdas.tools
except Exception:
    pass
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
        func = globals().get(tool_name) or globals().get(tool_name.lower())
        if func is None:
            print(f"⚠️ La función '{tool_name}' no está definida en globals(); intentar import dinámico...")
            # try importing the module under lambdas.tools.<snake_case>
            mod_name = f"lambdas.tools.{tool_name.lower()}"
            import traceback
            try:
                module = importlib.import_module(mod_name)
            except Exception as e:
                print(f"Import error for {mod_name}: {e}")
                print(traceback.format_exc())
                # try with simple snake-case conversion (Recomendar_Receta -> recomendar_receta)
                try:
                    snake = tool_name.replace(" ", "_").replace("-", "_").lower()
                    module = importlib.import_module(f"lambdas.tools.{snake}")
                except Exception as e2:
                    pass
                    # As a last resort, try loading the module directly from the filesystem path
                    try:
                        base = os.path.dirname(os.path.dirname(__file__))
                        tools_path = os.path.join(base, "tools")
                        snake = tool_name.replace(" ", "_").replace("-", "_").lower()
                        file_path = os.path.join(tools_path, f"{snake}.py")
                        if os.path.exists(file_path):
                            try:
                                spec = importlib.util.spec_from_file_location(f"lambdas.tools.{snake}", file_path)
                                module = importlib.util.module_from_spec(spec)
                                spec.loader.exec_module(module)
                            except Exception as e3:
                                print(f"File import failed for {file_path}: {e3}")
                                print(traceback.format_exc())
                                module = None
                        else:
                            print(f"❌ No se encontró archivo de módulo para tool {tool_name} en {file_path}: {e}; {e2}")
                            module = None
                    except Exception as e3:
                        print(f"❌ No se pudo cargar por archivo para tool {tool_name}: {e}; {e2}; {e3}")
                        print(traceback.format_exc())
                        module = None

            if module is not None:
                # Try to get the attribute by exact name, then case-insensitive fallback
                if hasattr(module, tool_name):
                    func = getattr(module, tool_name)
                else:
                    # search for attribute matching ignoring case/underscores
                    candidates = [name for name in dir(module) if name.lower().replace("_","") == tool_name.lower().replace("_","")]
                    if candidates:
                        func = getattr(module, candidates[0])
                    else:
                        # as last resort, try function named in snake_case
                        snake_fn = tool_name.replace(" ", "_").lower()
                        if hasattr(module, snake_fn):
                            func = getattr(module, snake_fn)
                        else:
                            func = None

            # If still not found, scan all files in lambdas/tools directory and try to locate the function
            if func is None:
                try:
                    tools_dir = os.path.join(os.path.dirname(__file__), "tools")
                    if os.path.isdir(tools_dir):
                        for fname in os.listdir(tools_dir):
                            if not fname.endswith(".py") or fname.startswith("__"):
                                continue
                            path = os.path.join(tools_dir, fname)
                            try:
                                spec = importlib.util.spec_from_file_location(f"lambdas.tools.{fname[:-3]}", path)
                                mod = importlib.util.module_from_spec(spec)
                                spec.loader.exec_module(mod)
                                # search for attribute matching tool_name ignoring case/underscores
                                for name in dir(mod):
                                    if name.lower().replace("_", "") == tool_name.lower().replace("_", ""):
                                        func = getattr(mod, name)
                                        print(f"✅ Found tool {tool_name} in file {fname} as attribute {name}")
                                        break
                                if func is not None:
                                    break
                            except Exception:
                                continue
                except Exception:
                    pass

        if func is None:
            return {"error": "tool_not_found", "tool": tool_name}

        # Ejecuta la función y captura su resultado
        try:
            # Prefer calling with signature (input_data, intention, processor, conn, session_id)
            result = func(intention, processor, conn, session_id)
        except TypeError:
            # try more legacy signatures
            try:
                result = func(intention)
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