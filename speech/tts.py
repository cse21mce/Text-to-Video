import edge_tts
import os
from moviepy.editor import AudioFileClip

# User defined modules
from logger import log_info, log_error, log_success
from utils import rename,restructure_srt,LANGUAGES,rootFolder

async def generate_tts_audio_and_subtitles(text: str, title: str, lang: str):
    """Generate TTS using edge-tts stream and save audio and subtitles."""
    if lang not in LANGUAGES:
        raise ValueError(f"Language '{lang}' is not supported.")
    
    voice = LANGUAGES[lang]["voice"]
    rate = LANGUAGES[lang]["rate"]
    pitch = LANGUAGES[lang]["pitch"]

    # Define output files
    output_dir = os.path.join(rootFolder, "output", rename(title))
    os.makedirs(output_dir, exist_ok=True)  # Ensure output directory exists
    audio_file_path = os.path.join(output_dir, f"{lang}.mp3")
    subtitle_file_path = os.path.join(output_dir, f"{lang}.srt")


    # Convert absolute paths to relative paths from the root folder
    relative_audio_path = os.path.relpath(audio_file_path, rootFolder)
    relative_subtitle_path = os.path.relpath(subtitle_file_path, rootFolder)

    # Ensure paths use `\` on Windows
    relative_audio_path = f"\\{relative_audio_path}"
    relative_subtitle_path = f"\\{relative_subtitle_path}"
    

    # Check if the audio and subtitle files already exist
    if os.path.exists(audio_file_path) and os.path.exists(subtitle_file_path):
        log_info(f"Audio and subtitles already exist for language '{lang}', returning existing file paths.")
        # Get the duration of the audio file
        audio = AudioFileClip(audio_file_path)
        duration = int(audio.duration)

        return {"audio": audio_file_path, "subtitle": subtitle_file_path, "duration":duration}  
    
    log_info(f"Started Speeching of '{title}' for language '{lang}'")

    try:
        # Initialize the communicator for streaming and subtitle generation
        communicate = edge_tts.Communicate(text, voice=voice, rate=rate, pitch=pitch)
        submaker = edge_tts.SubMaker()
        
        # Open files for audio and subtitles
        with open(audio_file_path, "wb") as audio_file, open(subtitle_file_path, "w", encoding="utf-8") as srt_file:
            # Stream the audio and feed the subtitles in real-time
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_file.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    submaker.feed(chunk)
            
            # Write subtitles to the file after streaming is complete
            srt_file.write(submaker.get_srt())
        

        # Get the duration of the audio file
        audio = AudioFileClip(audio_file_path)
        duration = int(audio.duration)

        # Reconstruct 
        restructure_srt(subtitle_file_path);
        log_success(f"Completed Speeching of '{title}' for language '{lang}'")
        
        # Return file paths (strings)
        return {"audio": relative_audio_path, "subtitle": relative_subtitle_path, "duration":duration }
    
    except Exception as e:
        log_error(f"Error during TTS generation: {str(e)}")
        raise RuntimeError(f"Error during TTS generation: {str(e)}")
    

# if __name__ == "__main__":
#     import asyncio

#     # Test the function with a sample title, text, and language
#     sample_text = "केंद्रीय संस्कृति और पर्यटन मंत्री श्री गजेंद्र सिंह शेखावत ने कल इलाहाबाद संग्रहालय में लघु चित्रों पर आधारित'भागवत'प्रदर्शनी का उद्घाटन किया। उन्होंने कहा कि हर कोई महाकुंभ के पवित्र और दिव्य अवसर को और भी भव्य और अद्वितीय बनाने का प्रयास कर रहा है प्रयागराज के इस ऐतिहासिक संग्रहालय द्वारा तैयार की गई'भागवत'प्रदर्शनी इस विशेष अवसर को सुशोभित करने का एक सार्थक प्रयास है। सबके सामूहिक प्रयास से ही यह अद्वितीय कुंभ दिव्य और भव्य बन रहा है संग्रहालय परिसर में स्थित शहीद चंद्र शेखर आजाद की प्रतिमा को श्रद्धांजलि देने के बाद केंद्रीय मंत्री ने'भागवत'प्रदर्शनी की समीक्षा की उन्होंने संग्रहालय की टीम को सुंदर व्यवस्था के लिए बधाई दी और कहा कि ये लघु चित्र दुनिया, मृत्यु के बाद के जीवन, समाज, कला और संस्कृति का एक साथ प्रतिनिधित्व करते हैं। प्रदर्शनी में संग्रहालय के समृद्ध संग्रह को कुंभ परंपरा और भगवान राम और कृष्ण के चरित्र के साथ मिश्रित किया गया है। श्री गजेंद्र सिंह शेखावत ने आगे कहा कि महाकुंभ के पवित्र और दिव्य अवसर को और भी भव्य और अनूठा बनाने के लिए हर कोई प्रयास कर रहा है प्रयागराज के इस ऐतिहासिक संग्रहालय द्वारा तैयार की गई'भागवत'प्रदर्शनी इस असाधारण अवसर को सुशोभित करने का एक सार्थक प्रयास है। इस प्रदर्शनी के माध्यम से महाकुंभ के आध्यात्मिक महत्व और भगवान राम से संबंधित कहानियों को प्रदर्शित किया जाता है यह प्रदर्शनी हमारे देश में मौजूद कला की गहराई को समझने का अवसर प्रदान करती है। केंद्रीय मंत्री ने कहा कि कुंभ भारत के भव्य रूप की एक झलक प्रदान करता है यह सभी धार्मिक मान्यताओं, पूजा, आस्था और सांस्कृतिक विचारधाराओं के लोगों को एक स्थान पर एक साथ लाता है। उन लोगों के लिए जो विभिन्न शासकों के तहत स्वतंत्रता पूर्व युग के दौरान भारत के विभिन्न हिस्सों में विभाजन की बात करते हैं, कुंभ भारत की एकता का शाश्वत प्रमाण है मंत्री ने यह भी उल्लेख किया कि महाकुंभ के दौरान काला ग्राम में'शाश्वत कुंभ'नामक एक प्रदर्शनी का प्रदर्शन किया गया था, जिसमें दिखाया गया था कि कुंभ ने देश को एकजुट करने के लिए कैसे काम किया है प्रदर्शनी के उद्घाटन के बाद केंद्रीय मंत्री ने प्रदर्शनी सूची भी जारी की इसके बाद उन्होंने आजाद पथ, मूर्तिकला कला दीर्घा और टेराकोटा कला दीर्घा का दौरा किया। संग्रहालय के निदेशक श्री राजेश प्रसाद ने संग्रहालय के समृद्ध इतिहास और संग्रहों के महत्व के बारे में जानकारी दी। केंद्रीय मंत्री ने संग्रहालय के प्रकाशनों, त्रैमासिक पत्रिका'विविध'और संग्रहालय में प्रवेश के लिए एक विशेष महाकुंभ टिकट का भी विमोचन किया इस कार्यक्रम में शहर के प्रतिष्ठित नागरिकों के साथ-साथ संग्रहालय के सभी अधिकारियों ने भाग लिया"
#     sample_title = "test"
#     sample_language = "hindi"

#     async def main():
#         try:
#             result = await generate_tts_audio_and_subtitles(sample_text, sample_title, sample_language)
#             print(f"Audio file path: {result['audio']}")
#             print(f"Subtitle file path: {result['subtitle']}")
#         except Exception as e:
#             print(f"An error occurred: {e}")

#     # Run the asynchronous main function
#     asyncio.run(main())
