import os
import textwrap
import tempfile
from moviepy.video.tools.subtitles import SubtitlesClip
from moviepy.video.fx.all import resize
from moviepy.config import change_settings
from moviepy.editor import ImageSequenceClip, concatenate_videoclips, concatenate_audioclips, CompositeVideoClip, AudioFileClip, CompositeAudioClip, VideoFileClip, TextClip
from moviepy.audio.fx.all import volumex
import numpy as np

# User defined modules
from utils import rename
from logger import log_info, log_warning, log_error, log_success
# Set ImageMagick binary path (required for TextClip on Windows)
change_settings({"IMAGEMAGICK_BINARY": r"C:\Program Files\ImageMagick-7.1.1-Q16-HDRI\magick.exe"})

# FONT = {
#     'english': 'fonts/font.otf',
#     'hindi': 'fonts/hindi.ttf',
#     'urdu': 'fonts/urdu.ttf',  # Ensure you have a Urdu-compatible font
# }

RESOLUTION = (720, 1280)  # Adjust as needed
OUTPUT_DIR = "output"

def wrap_text(text, max_width):
    """Wrap text into multiple lines based on max_width."""
    wrapper = textwrap.TextWrapper(width=max_width, break_long_words=True, break_on_hyphens=False)
    return wrapper.fill(text)

def generate_video(title, images, translations):
    output_videos = []

    # Background music and Intro Video path 
    background_music_path = "assets/background_music.mp3"
    intro_video_path = "assets/intro.mp4"

    # Create a directory to store the output videos
    output_dir = os.path.join(OUTPUT_DIR, rename(title))
    os.makedirs(output_dir, exist_ok=True)

    log_info(f"Started video generation for: {title}")
    
    for translation in translations:
        # Generate output path
        language = os.path.basename(translation['audio']).lstrip('\\').split('.')[0]
        output_video_path = os.path.join(output_dir, f"{language}.mp4")

        log_info(f"Processing translation for {language}...")

        # Check if video already exists and is valid
        if os.path.exists(output_video_path):
            try:
                with VideoFileClip(output_video_path) as video:
                    if video.duration > 0:
                        log_info(f"Video already exists for {language}, skipping generation")
                        output_videos.append(output_video_path)
                        continue
            except Exception as e:
                log_warning(f"Existing video for {language} appears corrupted ({str(e)}), regenerating...")
                if os.path.exists(output_video_path):
                    os.remove(output_video_path)

        clips = []

        # Add intro video if it exists
        intro_duration = 0
        if intro_video_path and os.path.exists(intro_video_path):
            try:
                intro_clip = VideoFileClip(intro_video_path)
                log_info(f"Loaded intro clip. Duration: {intro_clip.duration}, Size: {intro_clip.size}")
                
                if intro_clip.duration > 0 and intro_clip.size[0] > 0 and intro_clip.size[1] > 0:
                    intro_duration = intro_clip.duration
                    if intro_clip.size != RESOLUTION:
                        intro_clip = intro_clip.resize(RESOLUTION)
                    clips.append(intro_clip)
                else:
                    log_warning("Invalid intro clip detected")
                    intro_clip.close()
                    intro_duration = 0
            except Exception as e:
                log_error(f"Error loading intro clip: {e}")
                intro_duration = 0

        # Load the audio file
        audio_clip = AudioFileClip(translation['audio'].lstrip('\\'))
        main_content_duration = audio_clip.duration

        log_info(f"Audio duration for {language}: {main_content_duration} seconds")

        # Calculate the duration for each image
        image_duration = main_content_duration / len(images)

        # Resize all images
        resized_images = []
        for image in images:
            log_info(f"Resizing image: {image}")
            clip = ImageSequenceClip([image], durations=[image_duration])
            resized_clip = resize(clip, newsize=RESOLUTION)
            resized_images.append(resized_clip)

        # Create slideshow clip
        slideshow_clip = concatenate_videoclips(resized_images, method="compose")
        clips.append(slideshow_clip)

        # Verify clips
        valid_clips = [clip for clip in clips if clip.duration > 0 and hasattr(clip, 'size')]
        if not valid_clips:
            raise ValueError("No valid video clips to concatenate")

        # Concatenate clips
        final_video = concatenate_videoclips(valid_clips, method="compose")
        log_info(f"Final video duration: {final_video.duration} seconds")

        # Calculate total duration
        total_duration = intro_duration + main_content_duration

        # Handle background music
        if background_music_path and os.path.exists(background_music_path):
            music = AudioFileClip(background_music_path)
            
            if music.duration < total_duration:
                num_loops = int(np.ceil(total_duration / music.duration))
                music = concatenate_audioclips([music] * num_loops).subclip(0, total_duration)
            else:
                music = music.subclip(0, total_duration)
            
            music = music.fx(volumex, 0.3)
            
            if intro_duration > 0:
                silent_clip = AudioFileClip(background_music_path).subclip(0, intro_duration).fx(volumex, 0)
                delayed_audio = concatenate_audioclips([silent_clip, audio_clip])
            else:
                delayed_audio = audio_clip

            final_audio = CompositeAudioClip([delayed_audio, music])
        else:
            if intro_duration > 0:
                silent_clip = AudioFileClip(background_music_path).subclip(0, intro_duration).fx(volumex, 0)
                final_audio = concatenate_audioclips([silent_clip, audio_clip])
            else:
                final_audio = audio_clip

        final_video = final_video.set_audio(final_audio)

        # Handle subtitles with proper encoding
        subtitle_file = translation.get('subtitle').lstrip('\\')
        if subtitle_file and os.path.exists(subtitle_file):
            try:
                log_info(f"Processing subtitle file: {subtitle_file} for {language}")
                # First try UTF-8
                with open(subtitle_file, 'r', encoding='utf-8') as f:
                    subtitles_content = f.read()
            except UnicodeDecodeError:
                try:
                    # If UTF-8 fails, try UTF-16
                    with open(subtitle_file, 'r', encoding='utf-16') as f:
                        subtitles_content = f.read()
                except UnicodeDecodeError:
                    # If both fail, try with error handling
                    with open(subtitle_file, 'r', encoding='utf-8', errors='replace') as f:
                        subtitles_content = f.read()

            # Create temporary file with UTF-8 encoding
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.srt', encoding='utf-8') as temp_file:
                temp_file.write(subtitles_content)
                temp_file_path = temp_file.name

            def generator(txt):
                try:
                    wrapped_text = wrap_text(txt, max_width=30)
                    return TextClip(
                        wrapped_text, 
                        font='fonts/font.otf',  # Default to English font if language not specified
                        fontsize=50, 
                        color='yellow',
                        size=(RESOLUTION[0] * 0.9, None), 
                        method='caption', 
                        align='center', 
                        stroke_width=3, 
                        stroke_color='black'
                    )
                except Exception as e:
                    log_error(f"Error generating subtitle for text: {txt}")
                    log_error(f"Error details: {str(e)}")
                    # Return a blank clip of the same duration if there's an error
                    return TextClip(" ", fontsize=50, color='yellow')

            try:
                from moviepy.video.tools.subtitles import file_to_subtitles
                subs = file_to_subtitles(temp_file_path)
                subtitles = SubtitlesClip(subs, generator)
                
                if intro_duration > 0:
                    subtitles = subtitles.set_start(intro_duration)
                subtitles = subtitles.set_position(('center', 'bottom')).set_duration(main_content_duration)
                final_video = CompositeVideoClip([final_video, subtitles])
            except Exception as e:
                log_error(f"Error processing subtitles for {language}: {str(e)}")
                log_warning("Continuing without subtitles...")

            # Clean up temp file
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

        # Write final video
        log_info(f"Writing final video to: {output_video_path}")
        final_video.write_videofile(output_video_path, fps=24)
        
        # Clean up
        final_video.close()
        if 'intro_clip' in locals():
            intro_clip.close()
        audio_clip.close()
        if 'music' in locals():
            music.close()
        for clip in resized_images:
            clip.close()

        log_success(f"Video generation completed for {language}: {output_video_path}")
        output_videos.append(output_video_path)

    log_info(f"Video generation completed for all translations in {title}")
    return output_videos



# if __name__ == "__main__":
#     images = [
#         'https://upload.wikimedia.org/wikipedia/commons/thumb/c/c3/President_Droupadi_Murmu_official_portrait_higher_version.jpg/1200px-President_Droupadi_Murmu_official_portrait_higher_version.jpg',
#         'https://static.pib.gov.in/WriteReadData/specificdocs/photo/2021/aug/ph202183101.png',
#         'https://img.etimg.com/thumb/width-1200,height-1200,imgsize-384244,resizemode-75,msid-117580101/news/india/maha-kumbh-110-million-devotees-take-holy-dip-at-sangam-in-first-14-days.jpg',
#     ]

#     title = 'PRESIDENT_OF_INDIA_TO_VISIT_PRAYAGRAJ_TOMORROW'

#     translations = [
#         {'audio': 'output/PRESIDENT_OF_INDIA_TO_VISIT_PRAYAGRAJ_TOMORROW/english.mp3',
#          'subtitle': 'output/PRESIDENT_OF_INDIA_TO_VISIT_PRAYAGRAJ_TOMORROW/english.srt',
#          'lang': 'english'},
#         {'audio': 'output/PRESIDENT_OF_INDIA_TO_VISIT_PRAYAGRAJ_TOMORROW/hindi.mp3',
#          'subtitle': 'output/PRESIDENT_OF_INDIA_TO_VISIT_PRAYAGRAJ_TOMORROW/hindi.srt',
#         'lang': 'hindi'},
#         # {'audio': 'output/PRESIDENT_OF_INDIA_TO_VISIT_PRAYAGRAJ_TOMORROW/urdu.mp3',
#         #  'subtitle': 'output/PRESIDENT_OF_INDIA_TO_VISIT_PRAYAGRAJ_TOMORROW/urdu.srt',
#         #  'lang': 'urdu'},
#     ]

#     output_videos = generate_video(title, images, translations)
#     print("Videos created:")
#     for video in output_videos:
#         print(video)