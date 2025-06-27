import os
import logging
from dotenv import load_dotenv
from openai import OpenAI, OpenAIError
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type

# Load environment variable
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# Logger setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(2),
    retry=retry_if_exception_type(OpenAIError)
)
def call_openai_chat(
    system_prompt: str,
    user_prompt: str,
    model: str = "gpt-4o",
    temperature: float = 0.6,
    max_tokens: int = 1000
) -> str:
    """
    Production-grade wrapper for OpenAI ChatCompletion using v1+ SDK.
    Includes retry logic, structured logging, and usage tracking.
    """
    logger.info(f"🤖 Sending prompt to OpenAI [{model}]...")

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )

        content = response.choices[0].message.content.strip()

        # Token usage logging (API cost tracking)
        usage = response.usage
        logger.info(f"🧾 Token usage: Total={usage.total_tokens}, Prompt={usage.prompt_tokens}, Completion={usage.completion_tokens}")

        return content

    except OpenAIError as e:
        logger.error(f"❌ OpenAI API call failed: {e}")
        raise
