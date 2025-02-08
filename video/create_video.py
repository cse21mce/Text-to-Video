import os
import subprocess
from sys import platform
from moviepy.editor import ImageClip, concatenate_videoclips, CompositeVideoClip, AudioFileClip, CompositeAudioClip, VideoFileClip, TextClip
from moviepy.video.fx.all import crop, speedx
from moviepy.audio.fx.all import volumex
from PIL import Image
from gtts import gTTS
import numpy as np
import datetime
from typing import Dict, List
import asyncio
from pathlib import Path

from moviepy.config import change_settings

# Set ImageMagick binary path (required for TextClip on Windows)
change_settings({"IMAGEMAGICK_BINARY": r"C:\Program Files\ImageMagick-7.1.1-Q16-HDRI\magick.exe"})

# Set FFmpeg path based on platform
if platform == "linux":
    os.environ['FFMPEG_BINARY'] = '/usr/bin/ffmpeg'
elif platform == "win32":
    ffmpeg_path = r"C:\ffmpeg\bin\ffmpeg.exe"
    if os.path.exists(ffmpeg_path):
        os.environ['FFMPEG_BINARY'] = ffmpeg_path


def resize_image_with_imagemagick(input_path: str, output_path: str, size: tuple) -> None:
    """
    Resize an image using ImageMagick.

    Args:
        input_path (str): Path to the input image.
        output_path (str): Path to save the resized image.
        size (tuple): Target size as (width, height).
    """
    command = [
        'magick', input_path,
        '-resize', f'{size[0]}x{size[1]}^',
        '-gravity', 'center',
        '-extent', f'{size[0]}x{size[1]}',
        output_path
    ]
    subprocess.run(command, check=True)


def blur_image_with_imagemagick(input_path: str, output_path: str, blur_radius: int = 10) -> None:
    """
    Blur an image using ImageMagick.

    Args:
        input_path (str): Path to the input image.
        output_path (str): Path to save the blurred image.
        blur_radius (int): Blur intensity. Default is 10.
    """
    command = [
        'magick', input_path,
        '-blur', f'0x{blur_radius}',
        output_path
    ]
    subprocess.run(command, check=True)


def zoom_effect(image_path: str, duration: float, resolution: tuple, mode: str = 'in', speed: float = 2.5, fps: int = 24) -> ImageClip:
    """
    Create a zoom effect on an image.

    Args:
        image_path (str): Path to the input image.
        duration (float): Duration of the zoom effect.
        resolution (tuple): Video resolution as (width, height).
        mode (str): Zoom mode ('in' or 'out'). Default is 'in'.
        speed (float): Zoom speed. Default is 2.5.
        fps (int): Frames per second. Default is 24.

    Returns:
        ImageClip: A MoviePy ImageClip with the zoom effect.
    """
    temp_resized_path = f"temp_resized_{hash(image_path)}.png"
    resize_image_with_imagemagick(image_path, temp_resized_path, resolution)

    img = ImageClip(temp_resized_path).set_duration(duration)
    w, h = resolution
    zoom_factor = 1.5 if mode == 'in' else 1 / 1.5

    def effect(get_frame, t):
        zoom = 1 + (zoom_factor - 1) * t / duration
        size = (int(w * zoom), int(h * zoom))
        frame = get_frame(t)
        pil_frame = Image.fromarray(frame)
        pil_frame = pil_frame.resize(size, Image.Resampling.LANCZOS)
        left = (size[0] - w) // 2
        top = (size[1] - h) // 2
        pil_frame = pil_frame.crop((left, top, left + w, top + h))
        return np.array(pil_frame)

    os.remove(temp_resized_path)
    return img.fl(effect, apply_to=['mask'])


def create_clip(image_path: str, text: str, duration: float, resolution: tuple, font_path: str = None, font_size: int = 43) -> CompositeVideoClip:
    """
    Create a single video clip with image, text, and audio.

    Args:
        image_path (str): Path to the image.
        text (str): Text to display on the clip.
        duration (float): Duration of the clip.
        resolution (tuple): Video resolution as (width, height).
        font_path (str): Path to the font file. Default is None.
        font_size (int): Font size. Default is 43.

    Returns:
        CompositeVideoClip: A MoviePy CompositeVideoClip.
    """
    temp_audio = f"temp_audio_{hash(text)}.mp3"
    gTTS(text, lang='en').save(temp_audio)

    audio_clip = AudioFileClip(temp_audio)
    audio_clip = audio_clip.fx(volumex, 1.4).fx(speedx, 1.05)

    final_duration = max(duration, audio_clip.duration + 0.5)

    try:
        base = ImageClip('./background.png').set_duration(final_duration)
    except:
        base = ImageClip(np.zeros((resolution[1], resolution[0], 3)), duration=final_duration)

    image_clip = zoom_effect(image_path, final_duration, resolution)

    temp_blurred_path = f"temp_blurred_{hash(image_path)}.png"
    blur_image_with_imagemagick(image_path, temp_blurred_path, blur_radius=10)
    blurred_clip = ImageClip(temp_blurred_path).set_position(('center', 'center')).set_duration(final_duration)

    text_clip = TextClip(
        text,
        fontsize=font_size,
        color='white',
        font=font_path if font_path else 'Arial',
        size=(resolution[0] - 100, None),
        method='caption'
    ).set_position(('center', 'bottom')).set_duration(final_duration)

    final_clip = CompositeVideoClip([base, blurred_clip, image_clip, text_clip])
    final_clip = final_clip.set_audio(audio_clip)

    try:
        os.remove(temp_audio)
        os.remove(temp_blurred_path)
    except:
        pass

    return final_clip


def create_video(image_paths: List[str], texts: List[str], resolution: tuple = (608, 1080), output_path: str = None, background_music_path: str = None, intro_video_path: str = None) -> str:
    """
    Create a complete video from multiple images and texts.

    Args:
        image_paths (List[str]): List of paths to images.
        texts (List[str]): List of texts corresponding to each image.
        resolution (tuple): Video resolution as (width, height). Default is (608, 1080).
        output_path (str): Path to save the output video. Default is None.
        background_music_path (str): Path to background music. Default is None.
        intro_video_path (str): Path to an intro video. Default is None.

    Returns:
        str: Path to the generated video.
    """
    if len(image_paths) != len(texts):
        raise ValueError("Number of images must match number of texts")

    clips = []

    if intro_video_path and os.path.exists(intro_video_path):
        intro_clip = VideoFileClip(intro_video_path)
        if intro_clip.size != resolution:
            intro_clip = intro_clip.resize(resolution)
        clips.append(intro_clip)

    for img, txt in zip(image_paths, texts):
        min_duration = 4.0
        clip = create_clip(img, txt, min_duration, resolution)
        clips.append(clip)

        gap = ImageClip(np.zeros((resolution[1], resolution[0], 3)), duration=0.3)
        gap = gap.set_audio(None)
        clips.append(gap)

    video = concatenate_videoclips(clips, method="chain")

    if background_music_path and os.path.exists(background_music_path):
        music = AudioFileClip(background_music_path)
        if music.duration < video.duration:
            num_loops = int(np.ceil(video.duration / music.duration))
            music = concatenate_videoclips([music] * num_loops).subclip(0, video.duration)
        else:
            music = music.subclip(0, video.duration)

        music = music.fx(volumex, 0.3)
        final_audio = CompositeAudioClip([video.audio, music])
        video = video.set_audio(final_audio)

    if not output_path:
        date_str = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_path = f"output_video_{date_str}.mp4"

    video.write_videofile(output_path, fps=24)
    return output_path


def split_content_into_segments(content: str, max_chars: int = 100) -> List[str]:
    """
    Split content into segments for video generation.

    Args:
        content (str): The content to split.
        max_chars (int): Maximum characters per segment. Default is 100.

    Returns:
        List[str]: List of content segments.
    """
    words = content.split()
    segments = []
    current_segment = []
    current_length = 0

    for word in words:
        if current_length + len(word) + 1 <= max_chars:
            current_segment.append(word)
            current_length += len(word) + 1
        else:
            segments.append(" ".join(current_segment))
            current_segment = [word]
            current_length = len(word)

    if current_segment:
        segments.append(" ".join(current_segment))

    return segments


async def generate_language_video(lang: str, title: str, content: str, images: List[str], resolution: tuple = (608, 1080)) -> str:
    """
    Generate video for a specific language.

    Args:
        lang (str): Language code.
        title (str): Title of the video.
        content (str): Content of the video.
        images (List[str]): List of image paths.
        resolution (tuple): Video resolution as (width, height). Default is (608, 1080).

    Returns:
        str: Path to the generated video.
    """
    texts = split_content_into_segments(content)
    output_path = f"video_{lang}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"

    try:
        create_video(
            image_paths=images,
            texts=texts,
            resolution=resolution,
            output_path=output_path,
            background_music_path="assets/background_music.mp3",
            intro_video_path="assets/intro.mp4"
        )
        return output_path
    except Exception as e:
        raise Exception(f"Error generating video for {lang}: {str(e)}")


async def generate_video(_id: str, translations: Dict[str, Dict[str, str]], images: List[str] = None) -> Dict[str, str]:
    """
    Generate videos for each language in the translations.

    Args:
        _id (str): Unique identifier for the press release.
        translations (Dict[str, Dict[str, str]]): Dictionary containing translations for different languages.
        images (List[str]): List of image paths. Default is None.

    Returns:
        Dict[str, str]: Dictionary mapping language codes to video file paths.
    """
    if images is None:
        images = ["assets/image1.jpg"]  # Default placeholder image

    video_paths = {}

    for lang, translation in translations.items():
        try:
            video_path = await generate_language_video(
                lang=lang,
                title=translation['title'],
                content=translation['content'],
                images=images
            )
            video_paths[lang] = video_path
        except Exception as e:
            raise Exception(f"Failed to generate video for language {lang}: {str(e)}")

    return video_paths


# Example usage (for testing):
if __name__ == "__main__":
    async def test():
        translations = {
            "english": {
                "title": "Test Title",
                "summary": "This is a test content for video generation."
            },
            "hindi": {
                "title": "परीक्षण शीर्षक",
                "content": "यह वीडियो जनरेशन के लिए एक परीक्षण सामग्री है।"
            }
        }

        try:
            video_paths = await generate_video("test_id", translations)
            print("Generated videos:", video_paths)
        except Exception as e:
            print(f"Error: {str(e)}")

    asyncio.run(test())