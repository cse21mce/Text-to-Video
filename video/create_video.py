import os
from moviepy import *
import pysrt
import asyncio
# from logger import log_info, log_error, log_success

async def generate_video(_id, translations):
    try:
        clips = []
        for trans in translations:
            audio = AudioFileClip(trans['audio'])
            video = ColorClip(size=(1920, 1080), color=(0, 0, 0), duration=audio.duration)
            video = video.with_audio(audio)

            font_path = f"E:/Python/IITB/text-to-video/fonts/{trans['language']}.ttf"
            
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
            clips.append(final)
        
        # Concatenate all video clips
        final_video = concatenate_videoclips(clips)
        output_path = os.path.join("output", "videos", f"{_id}.mp4")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Write the video file
        final_video.write_videofile(output_path, fps=24)
        return output_path

    except Exception as e:
        print(f"Error in generate_video: {e}")
        raise


if __name__ == "__main__":
    translations = [
        {
            "language": "english",
            "audio": "E:\\Python\\IITB\\text-to-video\\speech\\output\\Prime_Minister_congratulates_all_the_Padma_awardees_of_2025\\english.mp3",
            "subtitle": "E:\\Python\\IITB\\text-to-video\\speech\\output\\Prime_Minister_congratulates_all_the_Padma_awardees_of_2025\\english.srt"
        }
    ]
    
    asyncio.run(generate_video("test_video", translations))