from transformers import PegasusTokenizer, PegasusForConditionalGeneration

# Importing custom logger
from logger import log_info, log_warning, log_error, log_success

# Load Pegasus model and tokenizer
MODEL_NAME = "google/pegasus-xsum"  # Choose between "google/pegasus-cnn_dailymail" or "google/pegasus-xsum"
try:
    tokenizer = PegasusTokenizer.from_pretrained(MODEL_NAME)
    model = PegasusForConditionalGeneration.from_pretrained(MODEL_NAME)
except Exception as e:
    log_error(f"Error loading Pegasus model: {e}")
    raise RuntimeError(f"Error loading Pegasus model: {e}")

def summarize_text(text: str, max_length: int, min_length: int) -> str:
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
        log_info("Starting text summarization")
        
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
        log_success("Text summarization completed successfully")
        return summary

    except Exception as e:
        log_error(f"Error during text summarization: {e}")
        raise RuntimeError(f"Error generating summary: {str(e)}")
