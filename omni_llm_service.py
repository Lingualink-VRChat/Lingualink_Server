import base64
import os
from openai import OpenAI
import copy
import json
import time
import tempfile # For handling temporary audio files
import re # ADDED: For regex operations in parsing

# --- SCRIPT CONFIGURATION ---
# Load from environment variables, with defaults
VLLM_SERVER_URL = os.getenv("VLLM_SERVER_URL", "http://192.168.8.6:8000") # Or your vLLM server address
MODEL_NAME = os.getenv("MODEL_NAME", "qwenOmni7") # Replace with your actual model name if different
API_KEY = os.getenv("API_KEY", "abc123")      # Your API key

# --- HELPER FUNCTIONS ---
def encode_audio_to_base64(audio_path):
    """Encodes a .wav audio file to a base64 string. Raises ValueError for non-wav files."""
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    if not audio_path.lower().endswith(".wav"):
        raise ValueError(f"Unsupported audio format: {audio_path}. Only .wav files are supported by this service.")

    audio_format = "wav"

    with open(audio_path, "rb") as audio_file:
        binary_data = audio_file.read()
        base64_encoded_data = base64.b64encode(binary_data)
        base64_string = base64_encoded_data.decode('utf-8')
    return base64_string, audio_format

# --- CORE API INTERACTION ---
def process_audio_with_omni(audio_path, system_prompt, user_prompt_text):
    """
    Encodes audio, prepares and sends a request to the OpenAI-compatible Omni model,
    and returns the structured response or error.
    """
    try:
        base64_encoded_audio, audio_format = encode_audio_to_base64(audio_path)
        print(f"Successfully encoded audio file: {audio_path} (Format: {audio_format})")
    except Exception as e:
        print(f"Error encoding audio: {e}")
        return {"status": "error", "message": f"Audio encoding error: {e}", "details": None}

    try:
        # Construct base_url ensuring it ends with /v1 correctly
        temp_vllm_server_url = VLLM_SERVER_URL.rstrip('/')
        if temp_vllm_server_url.endswith('/v1'):
            final_base_url = temp_vllm_server_url
        else:
            final_base_url = f"{temp_vllm_server_url}/v1"

        client = OpenAI(
            api_key=API_KEY,
            base_url=final_base_url
        )

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        user_content = []
        if user_prompt_text:
            user_content.append({"type": "text", "text": user_prompt_text})

        user_content.append({
            "type": "input_audio",
            "input_audio": {
                "data": base64_encoded_audio,
                "format": audio_format # Ensure this format is what your omni model expects (e.g., "wav", "mp3")
            },
        })
        messages.append({"role": "user", "content": user_content})
        
        payload_to_display = { # For logging, truncated
            "model": MODEL_NAME,
            "messages": copy.deepcopy(messages),
            "max_tokens": 200,
            "temperature": 0
        }
        for msg_log in payload_to_display["messages"]:
            if msg_log["role"] == "user" and isinstance(msg_log["content"], list):
                for content_item_log in msg_log["content"]:
                    if content_item_log.get("type") == "input_audio":
                        data_to_log = content_item_log["input_audio"]["data"]
                        if len(data_to_log) > 100:
                            content_item_log["input_audio"]["data"] = data_to_log[:100] + "...[TRUNCATED]"
        
        print(f"\nSending request to: {client.base_url}chat/completions")
        print("Payload (audio data truncated for brevity):")
        print(json.dumps(payload_to_display, indent=2))

        start_time = time.monotonic()
        chat_completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            max_tokens=200, # Increased for potentially longer transcriptions + translations
            temperature=0 
        )
        duration = time.monotonic() - start_time
        print(f"API call completed in {duration:.2f} seconds.")

        message_content = None
        if chat_completion.choices and len(chat_completion.choices) > 0:
            message_content = chat_completion.choices[0].message.content
            # Try to parse the content if it's expected to be structured
            
            # New parsing logic:
            # Initialize parsed_output with raw_text.
            # Then, attempt to parse key-value pairs from the message content.
            parsed_output = {"raw_text": message_content}
            current_key = None
            current_value_lines = []
            try:
                lines = message_content.strip().split('\n')
                for line_content in lines:
                    stripped_content_for_structure = line_content.strip()

                    if not stripped_content_for_structure:
                        if current_key:
                            current_value_lines.append("") # Preserve blank line in current value
                        continue

                    parts = re.split(r'[:：]', stripped_content_for_structure, maxsplit=1)

                    if len(parts) == 2: # Potential new key
                        new_key_candidate = parts[0].strip()
                        new_value_first_line = parts[1].strip()

                        if new_key_candidate: # It's a valid new key
                            if current_key: # Save previous key's content
                                parsed_output[current_key] = "\n".join(current_value_lines)
                            
                            current_key = new_key_candidate
                            current_value_lines = [new_value_first_line]
                        elif current_key: # Key part is empty (e.g. "  : value"), treat as continuation
                            current_value_lines.append(stripped_content_for_structure)
                        # else: key part is empty, no current_key. Ignored for structured.

                    elif current_key: # No colon, and we have an active key, so append
                        current_value_lines.append(stripped_content_for_structure)
                    # else: No colon, no active key (preamble). Ignored for structured.

                # After loop, save the last key
                if current_key:
                    parsed_output[current_key] = "\n".join(current_value_lines)
            
            except Exception as parse_error:
                # Log the error. parsed_output will still contain raw_text
                # and any items parsed successfully before the error.
                print(f"Could not fully parse model output into dict: {parse_error}")

            return {
                "status": "success",
                "duration_seconds": duration,
                "data": parsed_output
            }
        else:
            print("No valid choice found in response:")
            print(chat_completion)
            return {"status": "error", "message": "No valid choice in model response", "details": str(chat_completion)}

    except Exception as e:
        print(f"\n--- Error ---")
        error_message = f"An API call error occurred: {e}"
        print(error_message)
        response_details = None
        if hasattr(e, 'response') and e.response is not None:
            response_details = {"status_code": e.response.status_code}
            try:
                response_details["content"] = e.response.json()
            except ValueError:
                response_details["content"] = e.response.text
        return {"status": "error", "message": error_message, "details": response_details, "duration_seconds": time.monotonic() - start_time if 'start_time' in locals() else 0}

def generate_system_prompt(target_languages=None):
    """
    Generates a system prompt for audio processing, including transcription
    and translation to specified target languages.
    """
    if target_languages is None:
        target_languages = ["英文", "日文"] # Default target languages

    prompt_lines = [
        "你是一个高级的语音处理助手。你的任务是：",
        "1.首先将音频内容转录成其原始语言的文本。"
    ]

    for i, lang in enumerate(target_languages):
        prompt_lines.append(f"{i+2}. 将转录的文本翻译成{lang}。")
    prompt_lines.append("请按照以下格式清晰地组织你的输出：")
    prompt_lines.append("原文：")
    for lang in target_languages:
        prompt_lines.append(f"{lang}：")
        
    return "\n".join(prompt_lines)

DEFAULT_USER_QUERY = "请处理下面的音频。"

if __name__ == '__main__':
    # This part is for testing omni_llm_service.py directly
    # Create a dummy test.wav for this test
    if not os.path.exists("test.wav"):
        print("Please create a 'test.wav' file in the same directory to test omni_llm_service.py")
    else:
        print("Testing omni_llm_service.py with test.wav and default languages...")
        default_prompt = generate_system_prompt() # Uses default [英文, 日文]
        result_default = process_audio_with_omni("test.wav", default_prompt, DEFAULT_USER_QUERY)
        print("\n--- Test Result (Default Languages) ---")
        print(json.dumps(result_default, indent=2, ensure_ascii=False))

        print("\nTesting omni_llm_service.py with test.wav and custom languages ['日语', '英语']...")
        custom_languages = ["英文", "韩文","日文"]
        custom_prompt = generate_system_prompt(custom_languages)
        result_custom = process_audio_with_omni("test.wav", custom_prompt, DEFAULT_USER_QUERY)
        print("\n--- Test Result (Custom Languages) ---")
        print(json.dumps(result_custom, indent=2, ensure_ascii=False))