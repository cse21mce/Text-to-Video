import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
from IndicTransToolkit.processor import IndicProcessor 
import os
import asyncio
import time
from typing import Dict


# User-defined modules
from database.db import store_translation_in_db, check_translation_in_db, update_translation_status
from speech.tts import generate_tts_audio_and_subtitles
from logger import log_info, log_error, log_warning,log_success
from utils import split_sentences

os.environ['CUDA_VISIBLE_DEVICES'] = '2, 3'

# Device selection
DEVICE = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
torch.cuda.empty_cache()

# Model and tokenizer initialization
model_name = "ai4bharat/indictrans2-en-indic-1B"
tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True, force_download=False)
model = AutoModelForSeq2SeqLM.from_pretrained(model_name, trust_remote_code=True, force_download=False).to(DEVICE)

# Preprocessing
ip = IndicProcessor(inference=True)

src_lang = "eng_Latn"

tgt_langs = {
    "hindi": "hin_Deva",
    "urdu": "urd_Arab",
    "gujrati": "guj_Gujr",
    "marathi": "mar_Deva",
    "telugu": "tel_Telu",
    "kannada": "kan_Knda",
    "malayalam": "mal_Mlym",
    "tamil": "tam_Taml",
    "bengali": "ben_Beng",
}

async def translateIn(text, tgt_lang):
    try:
        # Preprocessing improvements
        if not text or not text.strip():
            log_warning(f"Empty text received for translation to {tgt_lang}")
            return ""

        # Intelligent sentence splitting with preservation of delimiters
        input_sentences = split_sentences(text)

        # Validate input sentences
        if not input_sentences:
            log_warning(f"No valid sentences found for translation to {tgt_lang}")
            return ""

        # Language mapping with error handling
        tgt_lang = tgt_langs.get(tgt_lang)
        if not tgt_lang:
            raise ValueError(f"Invalid target language: {tgt_lang}")

        # Batch preprocessing with error handling
        try:
            batch = ip.preprocess_batch(input_sentences, src_lang=src_lang, tgt_lang=tgt_lang)
        except Exception as preprocess_error:
            log_error(f"Preprocessing failed: {preprocess_error}")
            raise

        # Tokenization with optional truncation based on batch size
        max_length = 256
        if len(batch) > 10:  # Adjust max length for very long inputs
            max_length = min(512, max_length * 2)

        # Improved tokenization
        inputs = tokenizer(
            batch,
            truncation=True,
            padding="longest",
            max_length=max_length,
            return_tensors="pt",
            return_attention_mask=True,
        ).to(DEVICE)

        # Translation with enhanced generation parameters
        with torch.no_grad():
            generated_tokens = model.generate(
                **inputs,
                use_cache=True,
                min_length=0,
                max_length=max_length,
                num_beams=5,
                num_return_sequences=1,
                early_stopping=True,
                no_repeat_ngram_size=2,  # Reduce repetitions
            )

        # Decoding with error handling
        try:
            with tokenizer.as_target_tokenizer():
                generated_tokens = tokenizer.batch_decode(
                    generated_tokens.detach().cpu().tolist(),
                    skip_special_tokens=True,
                    clean_up_tokenization_spaces=True,
                )
        except Exception as decode_error:
            log_error(f"Token decoding failed: {decode_error}")
            raise

        # Postprocessing
        try:
            translations = ip.postprocess_batch(generated_tokens, lang=tgt_lang)
        except Exception as postprocess_error:
            log_error(f"Postprocessing failed: {postprocess_error}")
            raise

        # Advanced joining with punctuation preservation
        result = ' '.join(translations).strip()
        
        # Optional: Additional text cleaning
        result = result.replace(' .', '.').replace(' ,', ',')
        result = result.replace(' !', '!').replace(' ?', '?')

        return result

    except Exception as e:
        log_error(f"Comprehensive translation error for {tgt_lang}: {str(e)}")
        raise


async def translate_and_store(_id, title, content, summary, ministry, lang):
    try:
        existing_translation = check_translation_in_db(_id, lang)

        if existing_translation:
            log_warning(f"Translation for {lang} already exists for {title}. Skipping translation.")
            return

        log_info(f"Translation of {title} for {lang} started.")
        update_translation_status(_id, lang, "in_progress")

        # Perform translations in parallel
        log_info(f"Starting parallel translation for {lang}")
        translations = await asyncio.gather(
            translateIn(title, lang),
            translateIn(ministry, lang),
            translateIn(content, lang),
            translateIn(summary, lang)
        )
        
        # Unpack the results
        translated_title, translated_ministry, translated_content, translated_summary = translations
        log_success(f"Parallel translation completed for {lang}")

        # Generate TTS audio with error handling
        try:
            summary_audio = await generate_tts_audio_and_subtitles(translated_summary, f"{title}", lang)
        except Exception as audio_error:
            log_warning(f"TTS audio generation failed for {lang}: {audio_error}")
            summary_audio = {"audio": None, "subtitle": None}
        
        log_success(f"Translation of {title} for {lang} completed.")

        # Store the translation in the database
        store_translation_in_db(
            _id,
            lang,
            {
                "title": translated_title,
                "summary": translated_summary,
                "ministry": translated_ministry,
                "content": translated_content,
                "audio": summary_audio.get("audio"),
                "subtitle": summary_audio.get("subtitle"),
                "status": "completed",
            }
        )

        log_info(f"Translation of {title} for {lang} stored to the database.")

    except Exception as e:
        log_error(f"Failed to translate and store for {lang} - {str(e)}")
        update_translation_status(_id, lang, "failed")  # Update status on failure
        raise Exception(f"Failed to translate and store for {lang}: {e}")


# Configure maximum concurrent operations
MAX_CONCURRENT_TRANSLATIONS = 3

async def translate(_id: str, title: str, content: str, summary: str, ministry: str):
    """
    Translates content into multiple languages with controlled concurrency.
    
    Args:
        _id: Document ID
        title: Content title
        content: Main content
        summary: Content summary
        ministry: Ministry name
    """
    try:
        start_time = time.time()
        total_languages = len(tgt_langs)
        completed = 0

        # Create semaphore for rate limiting
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_TRANSLATIONS)

        async def controlled_translate(tgt_lang: str) -> Dict:
            """Wrapper for rate-limited translation"""
            nonlocal completed
            async with semaphore:
                try:
                    await translate_and_store(_id, title, content, summary, ministry, tgt_lang)
                    completed += 1
                    log_info(f"Progress: {completed}/{total_languages} languages completed")
                    return {"lang": tgt_lang, "status": "success"}
                except Exception as e:
                    log_error(f"Failed translation for {tgt_lang}: {str(e)}")
                    return {"lang": tgt_lang, "status": "failed", "error": str(e)}

        # Create tasks for each language translation
        translation_tasks = [
            controlled_translate(tgt_lang)
            for tgt_lang in tgt_langs
        ]
        
        # Execute translations with controlled concurrency
        results = await asyncio.gather(*translation_tasks, return_exceptions=True)
        
        # Process results
        successful = sum(1 for r in results if isinstance(r, dict) and r.get("status") == "success")
        failed = total_languages - successful
        
        execution_time = time.time() - start_time
        log_success(
            f"Translation complete for '{title}'\n"
            f"Total time: {execution_time:.2f} seconds\n"
            f"Successful: {successful}/{total_languages}\n"
            f"Failed: {failed}/{total_languages}"
        )

        # If any translations failed, log details
        if failed > 0:
            failed_langs = [r.get("lang") for r in results if isinstance(r, dict) and r.get("status") == "failed"]
            log_warning(f"Failed translations for languages: {', '.join(failed_langs)}")

        return results
        
    except Exception as e:
        log_error(f"Critical error in translation process: {e}")
        raise e






















# async def translate_and_store(_id, title, content, ministry, lang):
#     try:
#         existing_translation = check_translation_in_db(_id, lang)

#         if existing_translation:
#             log_warning(f"Translation for {lang} already exists for {title}. Skipping translation.")
#             return

#         log_info(f"Translation of {title} for {lang} started.")

#         update_translation_status(_id, lang, "in_progress")
        
#         # Perform translations
#         translated_title = await translateIn(title, lang)
#         # translated_summary = await translateIn(summary, lang)
#         translated_ministry = await translateIn(ministry, lang)
#         translated_content = await translateIn(content, lang)

#         # Start converting translated text to speech
#         # summary_audio = await generate_tts_audio_and_subtitles(translated_summary, f"summary_{title}", lang)
#         content_audio = await generate_tts_audio_and_subtitles(translated_content, f"content_{title}", lang)

#         log_success(f"Translation of {title} for {lang} completed.")

#         # Store the translation in the database
#         store_translation_in_db(
#             _id,
#             lang,
#             {
#                 "title": translated_title,
#                 # "summary": translated_summary,
#                 "ministry": translated_ministry,
#                 "content": translated_content,
#                 # "summary_audio": summary_audio.get("audio"),
#                 # "summary_subtitle": summary_audio.get("subtitle"),
#                 "content_audio": content_audio.get("audio"),
#                 "content_subtitle": content_audio.get("subtitle"),
#                 "status": "completed",
#             }
#         )

#         log_info(f"Translation of {title} for {lang} stored to the database.")

#     except Exception as e:
#         log_error(f"Failed to translate and store for {lang} - {str(e)}")
#         raise Exception(f"Failed to translate and store for {lang}: {e}")


# async def translate(_id, title, content, ministry):
#     try:
#         for tgt_lang in tgt_langs:
#             await translate_and_store(_id, title, content, ministry, tgt_lang)
#         log_success(f"Translations for {title} completed for all languages.")

#     except Exception as e:
#         log_error(f"Error translating {title}: {e}")
#         raise e
