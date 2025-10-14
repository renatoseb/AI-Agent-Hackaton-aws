import json
from typing import Dict, List, Any, Optional
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
import re
from prompts.tool_selection import get_tool_selection_prompt

class ResponseProcessor:
    def __init__(self, model, tokenizer):
        self.model = model
        self.tokenizer = tokenizer

    
    def process_request(self, bedrock_payload: str) -> Dict[str, Any]:
        
        formatted_prompt = bedrock_payload

        inputs = self.tokenizer(formatted_prompt, return_tensors="pt").to(self.model.device)

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                do_sample=False,
                temperature=0,
                max_new_tokens=300,
                pad_token_id=self.tokenizer.eos_token_id,
                eos_token_id=self.tokenizer.eos_token_id
            )


        input_length = inputs["input_ids"].shape[1]
        generated_tokens = outputs[0][input_length:]
        response_text = self.tokenizer.decode(generated_tokens, skip_special_tokens=True)

        return response_text

        



def format_tool_selection_prompt(chat_hist: str, tools: str, processor: ResponseProcessor):

    formatted_prompt = get_tool_selection_prompt(tools, chat_hist)
    with open("debug_prompt.txt", "w") as f:
        f.write(formatted_prompt)

    response = processor.process_request(formatted_prompt)

    cleaned = re.sub(r"```(?:json)?", "", response, flags=re.IGNORECASE).strip()
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if not match:
        raise ValueError("No se encontró un objeto JSON válido en el texto.")

    json_str = match.group(0)

    
    try:
        response = json.loads(json_str)
    except json.JSONDecodeError as e:
        response = response
    return {
        "content": [{"text": response, "type": "text"}],
        "role": "assistant",
        "stop_reason": "end_turn"
    }

def format_intention_catching_prompt(chat_hist: str, processor: ResponseProcessor) -> str:
    from prompts.intention_catching import catch_intention
    intention = catch_intention(chat_hist)
    response = processor.process_request(intention)
    return response.strip()