import os
import subprocess
import datetime
import logging
import requests
from moviepy.editor import (
    ImageClip, VideoFileClip, AudioFileClip, CompositeAudioClip, concatenate_videoclips
)
from PIL import Image

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Constants
TEMP_DIR = "temp_files"
RESOLUTION = (608, 1080)
INRO_PATH = "assets/intro.mp4"
BG_MUSIC_PATH = "assets/background_music.mp3"
FFMPEG_PATH = "ffmpeg"
os.makedirs(TEMP_DIR, exist_ok=True)


def download_image(url):
    """Download image from URL and save to temp directory."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        img_path = os.path.join(TEMP_DIR, f'{hash(url)}.jpg')
        with open(img_path, 'wb') as f:
            f.write(response.content)
        return img_path
    except requests.RequestException as e:
        logging.error(f"Failed to download image {url}: {e}")
        return None


def create_zoom_effect(image_path, duration, zoom_factor=1.5):
    """Apply zoom effect to an image."""
    try:
        img_clip = ImageClip(image_path).resize(RESOLUTION).set_duration(duration)
        return img_clip.set_position("center").fx(lambda clip: clip.resize(lambda t: 1 + (zoom_factor - 1) * t / duration))
    except Exception as e:
        logging.error(f"Error applying zoom effect to {image_path}: {e}")
        return None

def create_video_clip(image_path, audio_path):
    """Create a video clip from an image and match its duration to the audio file."""
    if image_path.startswith("http"):
        image_path = download_image(image_path)
        if not image_path:
            return None
    
    try:
        if not os.path.exists(audio_path):
            logging.warning(f"Audio file missing: {audio_path}")
            return None  # Skip this video if audio is missing

        audio_clip = AudioFileClip(audio_path)
        duration = audio_clip.duration  # Get full audio duration
        
        img_clip = create_zoom_effect(image_path, duration)  # Match duration to audio
        if not img_clip:
            return None

        return img_clip.set_audio(audio_clip)
    except Exception as e:
        logging.error(f"Error creating video clip: {e}")
        return None


def add_subtitles(video_path, subtitle_path, output_path):
    """Overlay subtitles on a video using FFmpeg."""
    if not os.path.exists(subtitle_path):
        logging.warning(f"Subtitle file missing: {subtitle_path}")
        return
    try:
        cmd = [
            FFMPEG_PATH, "-i", video_path,
            "-vf", f"subtitles='{subtitle_path}':force_style='FontSize=12,PrimaryColour=&HFFFFFF&,Outline=1'",
            "-c:a", "copy", output_path
        ]
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        logging.error(f"FFmpeg subtitle overlay failed: {e}")


def generate_video(images, translations):
    """Generate a final video by combining images, audio, intro, and subtitles."""
    clips = []
    
    if INRO_PATH and os.path.exists(INRO_PATH):
        try:
            clips.append(VideoFileClip(INRO_PATH).resize(RESOLUTION))
        except Exception as e:
            logging.error(f"Failed to load intro video: {e}")
    
    for translation in translations:
        for img in images:
            clip = create_video_clip(img, translation.get("audio"))
            if clip:
                clips.append(clip)
    
    if not clips:
        logging.error("No valid video clips generated.")
        return None
    
    try:
        final_video = concatenate_videoclips(clips, method="compose")
        
        if BG_MUSIC_PATH and os.path.exists(BG_MUSIC_PATH):
            music = AudioFileClip(BG_MUSIC_PATH).subclip(0, final_video.duration).volumex(0.2)
            final_video = final_video.set_audio(CompositeAudioClip([final_video.audio, music]))
        
        output_video_path = f"output_video_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        temp_video_path = os.path.join(TEMP_DIR, "temp.mp4")
        final_video.write_videofile(temp_video_path, fps=24)
        
        for translation in translations:
            subtitle_output = output_video_path.replace(".mp4", f"_{translation['lang']}.mp4")
            add_subtitles(temp_video_path, translation.get("subtitle"), subtitle_output)
        
        return output_video_path
    except Exception as e:
        logging.error(f"Error generating final video: {e}")
        return None


if __name__ == "__main__":
    images = [
        'https://static.pib.gov.in/WriteReadData/specificdocs/photo/2021/aug/ph202183101.png',
        'https://upload.wikimedia.org/wikipedia/commons/thumb/c/c3/President_Droupadi_Murmu_official_portrait_higher_version.jpg/1200px-President_Droupadi_Murmu_official_portrait_higher_version.jpg',
        'https://img.etimg.com/thumb/width-1200,height-1200,imgsize-384244,resizemode-75,msid-117580101/news/india/maha-kumbh-110-million-devotees-take-holy-dip-at-sangam-in-first-14-days.jpg',
    ]
     
    translations = [
        {'audio': 'output\\PRESIDENT_OF_INDIA_TO_VISIT_PRAYAGRAJ_TOMORROW\\english.mp3',
         'subtitle': 'output\\PRESIDENT_OF_INDIA_TO_VISIT_PRAYAGRAJ_TOMORROW\\english.srt'},
        # {'audio': 'output\\PRESIDENT_OF_INDIA_TO_VISIT_PRAYAGRAJ_TOMORROW\\hindi.mp3',
        #  'subtitle': 'output\\PRESIDENT_OF_INDIA_TO_VISIT_PRAYAGRAJ_TOMORROW\\hindi.srt'},
        # {'audio': 'output\\PRESIDENT_OF_INDIA_TO_VISIT_PRAYAGRAJ_TOMORROW\\urdu.mp3',
        # 'subtitle': 'output\\PRESIDENT_OF_INDIA_TO_VISIT_PRAYAGRAJ_TOMORROW\\urdu.mp3'}
    ]
    
    output_video = generate_video(
        images,
        translations
    )
    print(f"Video created: {output_video}")