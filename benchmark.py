import time
from datetime import datetime
from loguru import logger
from openai import OpenAI
import csv
from config import (OPENROUTER_API_KEY, API_URL, MODELS, CATEGORY_PROMPTS)
from jailbreaks import ALL_JAILBREAKS

# Set up logging
logger.add("logs/benchmark_run_final.log", rotation="1 MB")

client = OpenAI(
    base_url=API_URL,
    api_key=OPENROUTER_API_KEY,
)

def run_conversation(model: str, user_prompt: str, jailbreak_func=None):
    """
    Runs a conversation with the LLM via OpenRouter API.

    model: The model name (e.g., "openai/gpt-4o").
    base_system_prompt: The base system prompt (e.g., ethical AI instructions).
    user_prompt: The base user prompt (e.g., malicious request).
    jailbreak_func: Optional jailbreak function to apply.
    returns: (response_content, tokens_used, effective_prompt)
    """

    effective_prompt = jailbreak_func(user_prompt) if jailbreak_func else user_prompt

    messages = [
        {"role": "user", "content": effective_prompt}
    ]

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=500,
            temperature=1
        )
        logger.info(response)
        return response.choices[0].message.content, response.usage.total_tokens, effective_prompt
    except Exception as e:
        logger.error(f"Error with model {model}: {e}")
        return None, 0, None

def append_to_csv(filename, row_data):
    """Appends a single row to the CSV file (creates file with headers if it doesn't exist)."""
    file_exists = filename in globals().get('csv_files_written', set())  # Track if we've written to this file
    with open(filename, 'a', newline='') as csvfile:
        fieldnames = ["model", "category", "base_prompt", "effective_prompt", "jailbreak", "response", "tokens_used", "timestamp"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()  # Write headers only once
            globals()['csv_files_written'] = {filename}  # Mark as initialized
        writer.writerow(row_data)

def main():
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"logs/results_{timestamp}.csv"

    try:
        for category in CATEGORY_PROMPTS:
            print(category)

            prompts_for_category = CATEGORY_PROMPTS[category]

            for base_prompt in prompts_for_category:
                for model in MODELS:
                    # Baseline: No jailbreak
                    logger.info(f"Testing {model} with {category}, prompt: '{base_prompt}', and jailbreak: None")
                    response, tokens, effective_prompt = run_conversation(model, base_prompt, jailbreak_func=None)
                    row = {
                        "model": model,
                        "category": category,
                        "base_prompt": base_prompt,
                        "effective_prompt": effective_prompt,
                        "jailbreak": "None",
                        "response": response,
                        "tokens_used": tokens,
                        "timestamp": time.time()
                    }
                    append_to_csv(filename, row)  # Save progressively
                    time.sleep(5)

                    # Loop over all registered jailbreaks (applied to user prompt)
                    for jailbreak_func in ALL_JAILBREAKS:
                        logger.info(f"Testing {model} with {category}, prompt: '{base_prompt}', and jailbreak: {jailbreak_func.__name__}")
                        response, tokens, effective_prompt = run_conversation(model, base_prompt, jailbreak_func=jailbreak_func)
                        row = {
                            "model": model,
                            "category": category,
                            "base_prompt": base_prompt,
                            "effective_prompt": effective_prompt,
                            "jailbreak": jailbreak_func.__name__,
                            "response": response,
                            "tokens_used": tokens,
                            "timestamp": time.time()
                        }
                        append_to_csv(filename, row)  # Save progressively
                        time.sleep(1)

    except KeyboardInterrupt:
        logger.info("Interrupted by user. Saving partial results.")
    except Exception as e:
        logger.error(f"Unexpected error: {e}. Saving partial results.")

    logger.info(f"Benchmark complete (or interrupted). Results saved to {filename}")

if __name__ == "__main__":
    main()
