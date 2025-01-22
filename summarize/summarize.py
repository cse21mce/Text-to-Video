from transformers import PegasusTokenizer, PegasusForConditionalGeneration
import logging


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load Pegasus model and tokenizer
MODEL_NAME = "google/pegasus-xsum"  # Choose between "google/pegasus-cnn_dailymail" or "google/pegasus-xsum"
try:
    tokenizer = PegasusTokenizer.from_pretrained(MODEL_NAME)
    model = PegasusForConditionalGeneration.from_pretrained(MODEL_NAME)
except Exception as e:
    raise RuntimeError(f"Error loading Pegasus model: {e}")


def summarize_text(text: str, max_length: int = 60, min_length: int = 10) -> str:
    """
    Summarizes the given text using the Pegasus model.

    Args:
        text (str): The input text to summarize.
        max_length (int): The maximum length of the summary.
        min_length (int): The minimum length of the summary.

    Returns:
        str: The generated summary.
    """
    try:
        logging.info(f"Summarizing text started")
        # Tokenize the input text
        inputs = tokenizer(
            text,
            return_tensors="pt",
            max_length=1024,  # Pegasus can handle long inputs (up to 1024 tokens)
            truncation=True,
        )

        # Generate the summary
        summary_ids = model.generate(
            inputs.input_ids,
            max_length=max_length,
            min_length=min_length,
            length_penalty=2.0,
            num_beams=4,
            early_stopping=True,
        )

        # Decode the generated summary
        summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
        logging.info(f"Summarizing text completed")
        return summary

    except Exception as e:
        raise RuntimeError(f"Error generating summary: {str(e)}")

