from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
import torch

class ModelRetriever:
    def __init__(self):
        pass
    def get_model_and_tokenizer(self):

        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Using device: {device}")
        # Choose model - Try pre-quantized versions first:
        # Pre-quantized options (much smaller):
        # model_name = "microsoft/Phi-3-mini-4k-instruct"  # 3.8B, very efficient
        # model_name = "unsloth/gemma-2-2b-it-bnb-4bit"   # 2B, 4-bit quantized
        # model_name = "TheBloke/Llama-2-7b-Chat-GPTQ"    # 7B, GPTQ quantized

        # Original model (will be quantized on-the-fly):
        model_name = "google/gemma-2-9b-it"

        # Configure 8-bit quantization (reduces memory by ~50%)
        quantization_config = BitsAndBytesConfig(
            load_in_8bit=True,
            llm_int8_threshold=6.0,
            llm_int8_has_fp16_weight=False,
        )

        # Or 4-bit quantization (reduces memory by ~75%)
        # quantization_config = BitsAndBytesConfig(
        #     load_in_4bit=True,
        #     bnb_4bit_compute_dtype=torch.float16,
        #     bnb_4bit_use_double_quant=True,
        #     bnb_4bit_quant_type="nf4"
        # )

        # Load tokenizer and model with FP16 precision
        # tokenizer = AutoTokenizer.from_pretrained(model_name)
        # model = AutoModelForCausalLM.from_pretrained(
        #     model_name,
        #     dtype=torch.float16,  # Use FP16 for ~50% memory reduction
        #     device_map="auto",          # Automatically place on available devices
        #     low_cpu_mem_usage=True      # Reduce CPU memory during loading
        # )
        # 
        # print(f"Model loaded with FP16 precision on device: {model.device}")

        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            quantization_config=quantization_config,
            device_map="auto",  # Let it automatically choose device placement
            dtype=torch.float16,  # Use torch_dtype instead of dtype
            low_cpu_mem_usage=True
        )
        return model, tokenizer