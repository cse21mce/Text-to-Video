import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
from IndicTransToolkit.processor import IndicProcessor 
from summarize.summarize import summarize_text
import os

# User-defined modules
from database.db import store_translation_in_db, check_translation_in_db, update_translation_status
from speech.tts import generate_tts_audio_and_subtitles
from logger import log_info, log_error, log_warning,log_success

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
        # Split text into sentences, ensuring the last part is included
        input_sentences = text.split('.')
        if input_sentences[-1] == '':
            input_sentences = input_sentences[:-1]  # Remove trailing empty string if present

        tgt_lang = tgt_langs.get(tgt_lang)

        batch = ip.preprocess_batch(input_sentences, src_lang=src_lang, tgt_lang=tgt_lang)

        # Tokenization and encoding
        inputs = tokenizer(
            batch,
            truncation=True,
            padding="longest",
            return_tensors="pt",
            return_attention_mask=True,
        ).to(DEVICE)

        # Translation
        with torch.no_grad():
            generated_tokens = model.generate(
                **inputs,
                use_cache=True,
                min_length=0,
                max_length=256,
                num_beams=5,
                num_return_sequences=1,
            )

        # Decoding and postprocessing
        with tokenizer.as_target_tokenizer():
            generated_tokens = tokenizer.batch_decode(
                generated_tokens.detach().cpu().tolist(),
                skip_special_tokens=True,
                clean_up_tokenization_spaces=True,
            )

        translations = ip.postprocess_batch(generated_tokens, lang=tgt_lang)

        # Joining translations
        result = ''.join(translations)
        return result.strip()

    except Exception as e:
        log_error(f"Error during translation: {str(e)}")
        raise e

async def translate_and_store(_id, title, content, summary, ministry, lang):
    try:
        existing_translation = check_translation_in_db(_id, lang)

        if existing_translation:
            log_warning(f"Translation for {lang} already exists for {title}. Skipping translation.")
            return

        log_info(f"Translation of {title} for {lang} started.")

        update_translation_status(_id, lang, "in_progress")

        
        content_length = len(content.split())

        max_length = min(1024, max(300, content_length // 2))
        min_length = max(20, max(200, content_length // 4))
        
        # Perform translations
        translated_title = await translateIn(title, lang)
        translated_ministry = await translateIn(ministry, lang)
        translated_content = await translateIn(content, lang)
        translated_summary = await translateIn(summary, lang)

        # Start converting translated text to speech
        summary_audio = await generate_tts_audio_and_subtitles(translated_summary, f"{title}", lang)
        # content_audio = await generate_tts_audio_and_subtitles(translated_content, f"content_{title}", lang)

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
                # "content_audio": content_audio.get("audio"),
                # "content_subtitle": content_audio.get("subtitle"),
                "status": "completed",
            }
        )

        log_info(f"Translation of {title} for {lang} stored to the database.")

    except Exception as e:
        log_error(f"Failed to translate and store for {lang} - {str(e)}")
        raise Exception(f"Failed to translate and store for {lang}: {e}")

async def translate(_id, title, content, summary, ministry):
    try:
        for tgt_lang in tgt_langs:
            await translate_and_store(_id, title, content, summary, ministry, tgt_lang)
        log_success(f"Translations for {title} completed for all languages.")

    except Exception as e:
        log_error(f"Error translating {title}: {e}")
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
