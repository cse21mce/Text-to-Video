import os
from moviepy import *
import pysrt
import asyncio
# from logger import log_info, log_error, log_success

async def generate_video(_id, translations):
    try:
        output_paths = []

        for trans in translations:
            audio = AudioFileClip(trans['audio'])
            video = ColorClip(size=(1080, 1920), color=(0, 0, 0), duration=audio.duration)
            video = video.with_audio(audio)

            # font_path = f"E:/Python/IITB/text-to-video/fonts/{trans['language']}.ttf"
            font_path = f"E:/Python/IITB/text-to-video/fonts/font.otf"
            
            subs = pysrt.open(trans['subtitle'])
            subtitle_clips = []
            
            for sub in subs:
                start = sub.start.ordinal / 1000
                end = sub.end.ordinal / 1000
                duration = end - start

                # Create the text clip for subtitles
                txt_clip = (TextClip(
                    text=sub.text,
                    font_size=48,  # Set font size instead of conflicting `method='caption'`
                    font=font_path,  # Ensure font name is specified only once
                    color='white',
                    size=(1920, 100),  # Set bounding box for the text
                    text_align='center'
                )
                .with_position(('center', 'bottom'))
                .with_duration(duration)
                .with_start(start))
                
                subtitle_clips.append(txt_clip)
            
            # Combine video and subtitles
            final = CompositeVideoClip([video] + subtitle_clips)
        
            # Concatenate all video clips
            output_path = os.path.join("video", "output",{_id}, f"{trans['language']}.mp4")
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
            final.write_videofile(output_path, fps=24)
            output_paths.append(output_path)
        
        return output_paths

    except Exception as e:
        print(f"Error in generate_video: {e}")
        raise


if __name__ == "__main__":
    translations = [
        {
            "language": "english",
            "audio": "E:\\Python\\IITB\\text-to-video\\speech\\output\\Prime_Minister_congratulates_all_the_Padma_awardees_of_2025\\english.mp3",
            "subtitle": "E:\\Python\\IITB\\text-to-video\\speech\\output\\Prime_Minister_congratulates_all_the_Padma_awardees_of_2025\\english.srt"
        },
        {
            "language": "hindi",
            "audio": "E:\\Python\\IITB\\text-to-video\\speech\\output\\Prime_Minister_congratulates_all_the_Padma_awardees_of_2025\\hindi.mp3",
            "subtitle": "E:\\Python\\IITB\\text-to-video\\speech\\output\\Prime_Minister_congratulates_all_the_Padma_awardees_of_2025\\hindi.srt"
        }
    ]
    
    asyncio.run(generate_video("test_video", translations))