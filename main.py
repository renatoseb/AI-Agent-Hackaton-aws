from model.retrieve_model import ModelRetriever
from prompts.utils import ResponseProcessor, format_tool_selection_prompt, format_intention_catching_prompt
import torch
import json
import time
from lambdas.ejecutar_tool import ejecutar_tool
from db.tools import get_all_tools
from db.conn import connect
from db.messages import create_messages_table, insert_message
import uuid


def now_ts():
    return int(time.time() * 1000)

if __name__ == "__main__":
    # messages_log is an append-only list of event dicts. Each event has:
    # {"ts": <ms epoch>, "type": "user|log|llm_thought|tool_choice|tool_result|assistant", "content": <str|dict>, "meta": {...}}
    messages_log = []

    # Seed with initial system/user context if desired
    messages_log.append({"ts": now_ts(), "type": "log", "content": "Session started", "meta": {}})

    retriever = ModelRetriever()
    model, tokenizer = retriever.get_model_and_tokenizer()

    conn = connect()
    # Ensure messages table exists
    create_messages_table(conn)

    # generate a session id for this run
    session_id = str(uuid.uuid4())
    tools = get_all_tools(conn)
    tools_ = "".join([f"TOOL: {tool[0]} - {tool[1]}\n\n" for tool in tools])

    processor = ResponseProcessor(model, tokenizer)

    print("Escribe tu mensaje (o 'exit' para salir):")
    while True:
        user_input = input("> ").strip()
        if user_input.lower() in ("exit", "salir", "quit"):
            print("Saliendo...")
            break

        # Append user message
        ev = {"ts": now_ts(), "type": "user", "content": user_input, "meta": {}}
        messages_log.append(ev)
        # persist to DB
        try:
            insert_message(conn, session_id, ev["ts"], ev["type"], ev["content"], ev["meta"])
        except Exception as e:
            print("⚠️ Warning: failed to insert user message to DB:", e)

        # Build chat history JSON for the intention catching model 
        reduced_messages = []
        for ev in messages_log:
            # Normalize events into the simple messages format expected by the prompts
            if ev["type"] == "user":
                if isinstance(ev["content"], dict) and "text" in ev["content"]:
                    content_item = {"text": ev["content"]["text"], "type": "text"}
                else:
                    content_item = {"text": str(ev["content"]), "type": "text"}
                reduced_messages.append({"role": "user", "content": [content_item]})
            elif ev["type"] == "assistant":
                if isinstance(ev["content"], dict) and "text" in ev["content"]:
                    content_item = {"text": ev["content"]["text"], "type": "text"}
                else:
                    content_item = {"text": str(ev["content"]), "type": "text"}
                reduced_messages.append({"role": "assistant", "content": [content_item]})
            else:
                # for logs and other types include as system/user text entries
                reduced_messages.append({"role": "user", "content": [{"text": f"[{ev['type']}] {ev['content']}", "type": "text"}]})

        chat_hist = json.dumps({"messages": reduced_messages}, ensure_ascii=False)

        # Run intention catching (LLM returns a short sentence)
        intention_prompt = format_intention_catching_prompt(chat_hist, processor)
        ev = {"ts": now_ts(), "type": "llm_thought", "content": intention_prompt, "meta": {"step": "intention_catching"}}
        messages_log.append(ev)
        try:
            insert_message(conn, session_id, ev["ts"], ev["type"], ev["content"], ev["meta"])
        except Exception as e:
            print("⚠️ Warning: failed to insert llm_thought to DB:", e)

        # Select tool
        tool_response = format_tool_selection_prompt(intention_prompt, tools_, processor)
        ev = {"ts": now_ts(), "type": "tool_choice", "content": tool_response, "meta": {}}
        messages_log.append(ev)
        try:
            insert_message(conn, session_id, ev["ts"], ev["type"], ev["content"], ev["meta"])
        except Exception as e:
            print("⚠️ Warning: failed to insert tool_choice to DB:", e)

        # Execute tool and capture result (ejecutar_tool adapted to accept conn, session_id and processor)
        tool_result = ejecutar_tool(tool_response, intention_prompt, messages_log, conn=conn, session_id=session_id, processor=processor)
        ev = {"ts": now_ts(), "type": "tool_result", "content": tool_result, "meta": {}}
        messages_log.append(ev)
        try:
            insert_message(conn, session_id, ev["ts"], ev["type"], ev["content"], ev["meta"])
        except Exception as e:
            print("⚠️ Warning: failed to insert tool_result to DB:", e)

        # Optionally, print latest events
        print("--- Events so far ---")
        for ev in messages_log[-6:]:
            print(f"{ev['ts']} {ev['type']}: {ev['content']}")

        # Persist to a file for debugging / state between runs
        with open("messages_log.json", "w", encoding="utf-8") as f:
            json.dump(messages_log, f, ensure_ascii=False, indent=2)