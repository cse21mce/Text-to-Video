import os
import moviepy.editor as mp
import requests
import pysrt
from PIL import Image,ImageFilter
import numpy as np

# User defined modules
from moviepy.config import change_settings
from logger import log_info, log_warning, log_success
from utils import ensure_directory_exists

# Set ImageMagick binary path (required for TextClip on Windows)
change_settings({"IMAGEMAGICK_BINARY": r"C:\Program Files\ImageMagick-7.1.1-Q16-HDRI\magick.exe"})
def time_to_seconds(t):
    """Convert datetime.time object to seconds"""
    return t.hour * 3600 + t.minute * 60 + t.second + t.microsecond / 1000000


INTRO_PATH = "assets/intro.mp4"
HEADER_PATH = "assets/headers"
BGM_PATH = "assets/bgm.mp3"


def download_image(url, save_path):
    """Download an image from a URL if not already present."""
    if os.path.exists(save_path):
        log_warning(f"Image already exists: {save_path}")
        return save_path
    
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open(save_path, 'wb') as file:
            for chunk in response.iter_content(1024):
                file.write(chunk)
        log_success(f"Downloaded: {save_path}")
    else:
        log_info(f"Failed to download {url}")
    return save_path

def delete_images(images):
    """Delete images from the given list if they exist."""
    for image in images:
        if os.path.exists(image):
            os.remove(image)
            log_success(f"Deleted: {image}")
        else:
            log_warning(f"File not found: {image}")

def process_images(images):
    """Ensure all images are downloaded if they are URLs."""
    processed_images = []
    for img in images:
        if img.startswith('http'):
            filename = os.path.basename(img.split('?')[0])  # Handle URL parameters
            save_path = os.path.join("downloaded_images", filename)
            os.makedirs("downloaded_images", exist_ok=True)
            processed_image = download_image(img, save_path)
            if os.path.exists(processed_image):
                processed_images.append(processed_image)
            else:
                log_warning(f"Skipping missing image: {img}")
        else:
            processed_images.append(img)
    return processed_images

def resize_image_clip(clip, target_size):
    """Helper function to handle image resizing with proper aspect ratio preservation"""
    def resize_frame(frame):
        pil_image = Image.fromarray(frame)
        # Use LANCZOS resampling (replacement for deprecated ANTIALIAS)
        resized = pil_image.resize(target_size, Image.LANCZOS)
        return np.array(resized)
    return clip.fl_image(resize_frame)

def resize_and_blur_background(clip, target_size):
    """Resize the image clip while maintaining aspect ratio and adding blurred background"""
    video_width, video_height = target_size

    # Load image
    pil_image = Image.fromarray(clip.get_frame(0))  # Get the first frame as an image
    img_width, img_height = pil_image.size

    # Scale the image to match the target width
    scale_factor = video_width / img_width
    new_height = int(img_height * scale_factor)
    resized_img = pil_image.resize((video_width, new_height), Image.LANCZOS)

    # Convert back to array
    resized_frame = np.array(resized_img)

    # Create blurred background
    blurred_bg = pil_image.resize((video_width, video_height), Image.LANCZOS).filter(ImageFilter.GaussianBlur(20))
    blurred_bg_frame = np.array(blurred_bg)

    # Create final frame by overlaying resized image on top of blurred background
    final_frame = blurred_bg_frame.copy()
    y_offset = (video_height - new_height) // 2
    final_frame[y_offset:y_offset+new_height, :, :] = resized_frame  # Overlay resized image

    return mp.ImageClip(final_frame).set_duration(clip.duration)

def create_video(images, audio_path, srt_path, ministry, output_path):
    # Import numpy here to avoid any potential import issues
    if os.path.exists(output_path):
        log_warning(f"Video already exists skipping video generation: {output_path}")
        return

    processed_images = process_images(images)

    # Check if all input files exist
    for file_path in [*processed_images, audio_path, srt_path, INTRO_PATH, f"{HEADER_PATH}/{ministry}.png", BGM_PATH]:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Input file not found: {file_path}")

    try:
        # Load intro clip
        intro_clip = mp.VideoFileClip(INTRO_PATH)
        
        # Load audio
        # narration_audio = mp.AudioFileClip(audio_path)
        # Load audio
        narration_audio = mp.AudioFileClip(audio_path).set_start(intro_clip.duration)

        
        # Set resolution to 9:16 (e.g., 1080x1920)
        video_width, video_height = 1080, 1920
        
        # Load images and apply zoom effect
        image_clips = []
        duration_per_image = (narration_audio.duration - intro_clip.duration) / len(processed_images)
        
        for image in processed_images:
            # Load the image and create clip
            img_clip = mp.ImageClip(image).set_duration(duration_per_image)
            
            # Get original image dimensions
            img_size = Image.open(image).size
            
            # Calculate scaling factors
            scale_w = video_width / img_size[0]
            scale_h = video_height / img_size[1]
            scale = max(scale_w, scale_h)
            
            # Calculate new dimensions maintaining aspect ratio
            new_size = (int(img_size[0] * scale), int(img_size[1] * scale))
            
            # Resize the clip
            img_clip = resize_and_blur_background(img_clip, (video_width, video_height))
            
            # Center the clip and add effects
            img_clip = (img_clip
                       .set_position(("center", "center"))
                       .fx(mp.vfx.fadein, 0.5)
                       .fx(mp.vfx.fadeout, 0.5))
            
            image_clips.append(img_clip)
        
        # Concatenate intro and image sequence
        video = mp.concatenate_videoclips([intro_clip] + image_clips, method="compose")
        
        # Create header overlay with proper sizing
        header_clip = mp.ImageClip(f"{HEADER_PATH}/{ministry}.png")
        header_size = (video_width, int(video_width * 0.2))  # 15% of width for height
        header_overlay = (resize_image_clip(header_clip, header_size)
                        .set_duration(video.duration - intro_clip.duration)
                        .set_position(("center", "top")))
        
        video = mp.CompositeVideoClip([
            video.set_duration(video.duration),
            header_overlay.set_start(intro_clip.duration)
        ])
        
        # Add subtitles
        subtitles = pysrt.open(srt_path)
        subtitle_clips = []
        
        for sub in subtitles:
            start_seconds = time_to_seconds(sub.start.to_time())+ intro_clip.duration
            end_seconds = time_to_seconds(sub.end.to_time())+ intro_clip.duration
            duration = end_seconds - start_seconds
            txt_clip = (mp.TextClip(
                sub.text,
                fontsize=85,
                color='orange',
                stroke_color='black',
                stroke_width=3,
                size=(int(video_width*0.8), None),
                method='caption',
                font='Hindi.ttf' if os.name == 'nt' else 'Arial'  # Handle different OS font names
            ).set_position(("center", 0.8),relative=True)
             .set_start(start_seconds)
             .set_duration(duration))
            
            subtitle_clips.append(txt_clip)
        
        # Merge subtitles with video
        video = mp.CompositeVideoClip([video] + subtitle_clips)
        
        # Add background music
        bgm_audio = mp.AudioFileClip(BGM_PATH).set_duration(narration_audio.duration).volumex(0.3).set_start(intro_clip.duration)
        final_audio = mp.CompositeAudioClip([intro_clip.audio,narration_audio, bgm_audio])
        video = video.set_audio(final_audio)
        # video = video.set_audio(final_audio).fx(mp.vfx.audio_fadein, 1.0)

        ensure_directory_exists(os.path.dirname(output_path))
        
        # Export the final video
        video.write_videofile(
            output_path,
            codec="libx264",
            fps=30,
            audio_codec="mp3",
            threads=4,
            preset='medium'  # Balance between speed and quality
        )
        
    finally:
        # Clean up resources
        try:
            intro_clip.close()
            narration_audio.close()
            bgm_audio.close()
            video.close()
            for clip in image_clips:
                clip.close()
            for clip in subtitle_clips:
                clip.close()
        except:
            pass

# if __name__ == "__main__":
#     create_video(
#         ["i1.jpg", "i2.jpg", "i3.jpg"],
#         "hindi.mp3",
#         "hindi.srt",
#         "Ministry of Defence",
#         "output/hindi.mp4"
#     )