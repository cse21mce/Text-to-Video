import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
from IndicTransToolkit.processor import IndicProcessor 
import os
import asyncio
import time
from typing import Dict
from torch.amp import autocast

from database.db import store_translation_in_db, check_translation_in_db, update_translation_status
from speech.tts import generate_tts_audio_and_subtitles
from logger import log_info, log_error, log_warning, log_success
from utils import split_sentences

os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "max_split_size_mb:128,garbage_collection_threshold:0.8"

DEVICE = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
torch.cuda.empty_cache()

model_name = "ai4bharat/indictrans2-en-indic-1B"
tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)

model = AutoModelForSeq2SeqLM.from_pretrained(
    model_name,
    trust_remote_code=True,
    torch_dtype=torch.float16,
    low_cpu_mem_usage=True,
    use_cache=True  # Required for gradient checkpointing
).to(DEVICE)

# Enable gradient checkpointing using new format
model._set_gradient_checkpointing(False)

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
        if not text or not text.strip():
            log_warning(f"Empty text received for translation to {tgt_lang}")
            return ""

        input_sentences = split_sentences(text)
        if not input_sentences:
            log_warning(f"No valid sentences found for translation to {tgt_lang}")
            return ""

        tgt_lang = tgt_langs.get(tgt_lang)
        if not tgt_lang:
            raise ValueError(f"Invalid target language: {tgt_lang}")

        # Process text in smaller chunks
        chunk_size = 10
        translations = []
        
        for i in range(0, len(input_sentences), chunk_size):
            chunk = input_sentences[i:i + chunk_size]
            
            try:
                batch = ip.preprocess_batch(chunk, src_lang=src_lang, tgt_lang=tgt_lang)
            except Exception as e:
                log_error(f"Preprocessing failed: {e}")
                raise

            max_length = 256
            inputs = tokenizer(
                batch,
                truncation=True,
                padding=True,
                max_length=max_length,
                return_tensors="pt",
                return_attention_mask=True,
            ).to(DEVICE)

            with autocast(device_type="cuda:0"):
                with torch.no_grad():
                    generated_tokens = model.generate(
                        **inputs,
                        use_cache=True,
                        min_length=0,
                        max_length=max_length,
                        num_beams=2,
                        length_penalty=0.6,
                        early_stopping=True,
                        no_repeat_ngram_size=2,
                    )

            try:
                with tokenizer.as_target_tokenizer():
                    decoded = tokenizer.batch_decode(
                        generated_tokens.detach().cpu(),
                        skip_special_tokens=True,
                        clean_up_tokenization_spaces=True,
                    )
                chunk_translations = ip.postprocess_batch(decoded, lang=tgt_lang)
                translations.extend(chunk_translations)
            except Exception as e:
                log_error(f"Decoding/postprocessing failed: {e}")
                raise

            torch.cuda.empty_cache()

        result = ' '.join(translations).strip()
        result = result.replace(' .', '.').replace(' ,', ',')
        result = result.replace(' !', '!').replace(' ?', '?')
        return result

    except Exception as e:
        log_error(f"Translation error for {tgt_lang}: {str(e)}")
        raise

async def translate_and_store(_id, title, summary, ministry, lang):
    try:
        translation = check_translation_in_db(_id, lang)
        if translation:
            log_warning(f"Translation exists for {lang}, {title}")
            return {**translation,"language":lang}

        log_info(f"Starting translation for {title} in {lang}")
        update_translation_status(_id, lang, "in_progress")

        translations = await asyncio.gather(
            translateIn(title, lang),
            translateIn(ministry, lang),
            translateIn(summary, lang)
        )
        
        translated_title, translated_ministry,  translated_summary = translations
        log_success(f"Translation completed for {lang}")

        try:
            summary_audio = await generate_tts_audio_and_subtitles(translated_summary, f"{title}", lang)
        except Exception as e:
            log_warning(f"TTS failed for {lang}: {e}")
            summary_audio = {"audio": None, "subtitle": None}

        translations.append(summary_audio)

        store_translation_in_db(
            _id,
            lang,
            {
                "title": translated_title,
                "summary": translated_summary,
                "ministry": translated_ministry,
                "audio": summary_audio.get("audio"),
                "subtitle": summary_audio.get("subtitle"),
                "status": "completed",
            }
        )

        log_info(f"Stored translation for {title} in {lang}")

        return {
                "language": lang,
                "title": translated_title,
                "audio": summary_audio.get("audio"),
                "subtitle": summary_audio.get("subtitle"),
                "status": "completed",
            }

    except Exception as e:
        log_error(f"Failed translation for {lang}: {e}")
        update_translation_status(_id, lang, "failed")
        raise

MAX_CONCURRENT_TRANSLATIONS = 3

async def translate(_id: str, title: str, summary: str, ministry: str):
    try:
        start_time = time.time()
        total_languages = len(tgt_langs)
        completed = 0
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_TRANSLATIONS)

        async def controlled_translate(tgt_lang: str) -> Dict:
            nonlocal completed
            async with semaphore:
                try:
                    translation_data = await translate_and_store(_id, title, summary, ministry, tgt_lang)
                    completed += 1
                    log_info(f"Progress: {completed}/{total_languages}")
                    return {**translation_data}
                except Exception as e:
                    log_error(f"Failed {tgt_lang}: {str(e)}")
                    return {"lang": tgt_lang, "status": "failed", "error": str(e)}

        translation_tasks = [controlled_translate(lang) for lang in tgt_langs]
        results = await asyncio.gather(*translation_tasks, return_exceptions=True)

        
        successful = sum(1 for r in results if isinstance(r, dict) and r.get("status") == "success")
        failed = total_languages - successful
        
        execution_time = time.time() - start_time
        log_success(
            f"Translation complete for '{title}'\n"
            f"Time: {execution_time:.2f}s\n"
            f"Success: {successful}/{total_languages}\n"
            f"Failed: {failed}/{total_languages}"
        )

        if failed > 0:
            failed_langs = [r.get("lang") for r in results if isinstance(r, dict) and r.get("status") == "failed"]
            log_warning(f"Failed languages: {', '.join(failed_langs)}")

        return results
        
    except Exception as e:
        log_error(f"Critical error: {e}")
        raise e
    



    