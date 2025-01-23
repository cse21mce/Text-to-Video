from openai import OpenAI
import os
from dotenv import load_dotenv

# user defined modules
from logger import log_info, log_error,log_success

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def summarize_text(text: str, max_length: int, min_length: int) -> str:
    try:
        log_info(f"Summary Generation started")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that provides concise summaries."
                },
                {
                    "role": "user",
                    "content": f"""Please provide a concise summary of the following text. The summary should be between {min_length} and {max_length} characters: {text}"""
                }
            ],
            temperature=0.7,
            max_tokens=max_length
        )
        log_success(f"Summary Generation completed")
        return response.choices[0].message.content.strip()

    except Exception as e:
        log_error(f"Error generating summary: {str(e)}")
        raise RuntimeError(f"Error generating summary: {str(e)}")
