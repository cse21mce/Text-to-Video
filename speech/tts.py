import edge_tts
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Your provided LANGUAGES dictionary
LANGUAGES = {
    "english": {
        "voice": "en-IN-NeerjaNeural",
        "rate": "+5%",
        "pitch": "-5Hz",
        "generate_subtitles": True
    },
    "hindi": {
        "voice": "hi-IN-SwaraNeural",
        "rate": "+5%",
        "pitch": "-5Hz",
        "generate_subtitles": True
    },
    "urdu": {
        "voice": "ur-IN-GulNeural",
        "rate": "+5%",
        "pitch": "-5Hz",
        "generate_subtitles": True
    },
    "gujrati": {
        "voice": "gu-IN-NiranjanNeural",
        "rate": "+5%",
        "pitch": "-5Hz",
        "generate_subtitles": True
    },
    "marathi": {
        "voice": "mr-IN-AarohiNeural",
        "rate": "+5%",
        "pitch": "-5Hz",
        "generate_subtitles": True
    },
    "telugu": {
        "voice": "te-IN-MohanNeural",
        "rate": "+5%",
        "pitch": "-5Hz",
        "generate_subtitles": True
    },
    "kannada": {
        "voice": "kn-IN-GaganNeural",
        "rate": "+5%",
        "pitch": "-5Hz",
        "generate_subtitles": True
    },
    "malayalam": {
        "voice": "ml-IN-MidhunNeural",
        "rate": "+5%",
        "pitch": "-5Hz",
        "generate_subtitles": True
    },
    "tamil": {
        "voice": "ta-IN-PallaviNeural",
        "rate": "+5%",
        "pitch": "-5Hz",
        "generate_subtitles": True
    },
    "bengali": {
        "voice": "bn-IN-TanishaaNeural",
        "rate": "+5%",
        "pitch": "-5Hz",
        "generate_subtitles": True
    },
}


async def generate_tts_audio_and_subtitles(text: str, lang: str):
    """Generate TTS using edge-tts stream and save audio and subtitles."""
    if lang not in LANGUAGES:
        raise ValueError(f"Language '{lang}' is not supported.")
    
    voice = LANGUAGES[lang]["voice"]
    rate = LANGUAGES[lang]["rate"]
    pitch = LANGUAGES[lang]["pitch"]
    
    output_file = f"output/audio_{lang}.mp3"
    subtitle_file = f"output/audio_{lang}.srt"

    try:
        # Initialize the communicator for streaming and subtitle generation
        communicate = edge_tts.Communicate(text, voice=voice, rate=rate, pitch=pitch)
        submaker = edge_tts.SubMaker()
        
        # Open files for audio and subtitles
        with open(output_file, "wb") as audio_file, open(subtitle_file, "w", encoding="utf-8") as srt_file:
            # Stream the audio and feed the subtitles in real-time
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_file.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    submaker.feed(chunk)
            
            # Write subtitles to the file after streaming is complete
            srt_file.write(submaker.get_srt())
        
        return {"message": f"TTS generated successfully with {voice} and saved to {output_file}, subtitles saved to {subtitle_file}"}
    
    except Exception as e:
        raise RuntimeError(f"Error during TTS generation: {str(e)}")