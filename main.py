from moviepy.audio.fx.audio_fadeout import audio_fadeout
from moviepy.audio.fx.audio_fadein import audio_fadein
from moviepy.video.tools.subtitles import SubtitlesClip
from tiktok_downloader import download_tiktoks
from moviepy.editor import VideoFileClip, CompositeVideoClip, TextClip, AudioFileClip, CompositeAudioClip, ImageClip
from moviepy.config import change_settings
from datetime import timedelta
from util_voice import Voice, tts
from pilmoji import Pilmoji
from groq import Groq
from PIL import ImageFont, Image

import numpy as np

import requests
import asyncio
import whisper
import random
import shutil
import json
import sys
import os
import re



change_settings({"IMAGEMAGICK_BINARY": r"C:\\Program Files\\ImageMagick-7.1.1-Q16-HDRI\\magick.exe"})

# Util for accurate caption file generation
def util_format_time(seconds: float) -> str:
    """Formats time in seconds to SRT format hh:mm:ss,SSS."""
    td = timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    milliseconds = int(td.microseconds / 1000)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"


# This util randomly capitalizes certain words and removes punctuation marks
def util_enhance_srt(srt_path):

    # emojis = ["\U0001F600", "\U0001F914", "\U0001F975"]  # List of emojis to choose from

    with open(srt_path, "r", encoding="utf-8") as f: lines = f.readlines()
    
    # Choose random lines to add emojis
    enhanced_lines = []
    for line in lines:
        if line.strip() and not bool(re.match(r'^\d+', line.strip())): # Only add emojis to non-empty lines that do not start with an integer
            line = line.replace('.', '').replace(',', '')
            if random.random() < 0.25: # 25% chance to capitalize a line
                line = line.upper()

            # if random.random() < 0.25: # 25% chance to add an emoji to a line
            #     emoji = random.choice(emojis)
            #     line = f"{emoji} {line.strip()} {emoji}\n"

        enhanced_lines.append(line)

    with open(srt_path, "w", encoding="utf-8") as f: f.writelines(enhanced_lines)



def util_subtitle_compiler(srt_path, color):

    # Create an instance of WordBouncer
    bouncer = UtilWordBouncer()

    method = "caption"
    font = "Comic-Sans-MS-Bold"
    fontsize = 80
    align = "center"

    subtitles_stroke_black = SubtitlesClip(srt_path, lambda txt: TextClip(txt, method=method, font=font, fontsize=fontsize, align=align, stroke_width=12, stroke_color="black").set_duration(.3).resize(lambda t : bouncer.bounce(t, txt)))
    subtitles = SubtitlesClip(srt_path, lambda txt: TextClip(txt, method=method, font=font, fontsize=fontsize, align=align, color=color).set_duration(.3).resize(lambda t : bouncer.bounce(t, txt)))

    return subtitles_stroke_black, subtitles



class UtilWordBouncer:
    def __init__(self):
        self.previous_word = None
        self.time_elapsed = 0
        self.max_t = 0


        self.small = 0.6
        self.medium = 1.0
        self.large = 1.1

    def bounce(self, t, txt):

        if self.max_t <  t: self.max_t = t
        if self.previous_word is not None and txt != self.previous_word:

            self.time_elapsed = self.max_t
            result = self.small
            
        else:

            time_remaining = self.max_t - self.time_elapsed
            if time_remaining < 0.1:
                t = (0.1 - time_remaining) / 0.1
                result = self.small + t * (self.large - self.small)
            elif time_remaining < 0.2:
                t = (time_remaining - 0.1) / 0.1
                result = self.large - t * (self.large - 1.0)
            else:
                result = 1.0

        # Update the previous word to the current word
        self.previous_word = txt
        return result


def make_emoji_image(emoji):
    emoji_font = ImageFont.truetype("data//NotoColorEmoji-Regular.ttf", random.randint(48, 200))
    text_size = emoji_font.getsize(emoji.strip())
    image = Image.new("RGBA", text_size, (0, 0, 0, 0))
    with Pilmoji(image) as pilmoji:
        pilmoji.text((0, 0), emoji.strip(), (0, 0, 0), emoji_font)
    return np.array(image)


def create_random_emoji_clips(video_duration):
    """
    Creates a list of ImageClips with emojis that appear at random times and positions.
    """
    emojis = [
        ["😤", "😂", "😍", "😎", "😢", "😡"],
        ["😊", "😂", "🤔", "🤢", "🤮", "🥵"],
        ["🤯", "😩", "😍", "😎", "💀", "😡"],
        ["🤯", "🤑", "😍", "🤢", "💀", "🤩"]
    ]

    clips = []

    emoji_set = random.choice(emojis)

    for _ in range(int(video_duration/2)):
        # Create the emoji image

        clip_duration = random.randint(2, 6)/10

        emoji_image = make_emoji_image(random.choice(emoji_set))
        
        # Create an ImageClip from the emoji image
        emoji_clip = ImageClip(emoji_image, duration=clip_duration)
        
        # Random start time within the video duration
        start_time = random.uniform(0, video_duration - clip_duration)
        
        # Random position within the video frame
        pos_x = random.choice([0.1, 0.8])  # Relative positions from 0.1 to 0.9
        pos_y = random.uniform(0.75, 0.85)
        
        # Set start time and position
        emoji_clip = emoji_clip.set_start(start_time).set_position((pos_x, pos_y), relative=True)
        
        clips.append(emoji_clip)
    
    return clips


def generate_tiktok_without_speech(input_file_path, output_file_path, video_intro, video_outro, ai_voice):

    # First step: generate intro audio
    tts(video_intro, ai_voice, "temp//temp_intro.mp3")

    # Second step: generate captions from the generated intro audio
    i = 0
    model = whisper.load_model("base")
    transcribe = model.transcribe(audio="temp//temp_intro.mp3", word_timestamps=True, language="en")
    for segment in transcribe['segments']:
        for word in segment['words']:

            i += 1
            text = word["word"]
            word = f"{i}\n{util_format_time(word["start"])} --> {util_format_time(word["end"]) }\n{text[1:] if text[0] == ' ' else text}\n\n"
            with open("temp//temp.srt", "a", encoding="utf-8") as f: f.write(word)

    util_enhance_srt("temp//temp.srt") # Remove punctuation marks and randomize capitalization

    # Third step: add the captions to the video
    subtitles_stroke_black, subtitles = util_subtitle_compiler("temp//temp.srt", "Yellow")
    subtitle_height = 0.25 # 25% of the video height

    emoji_clips = create_random_emoji_clips(video_duration=VideoFileClip(input_file_path).duration)

    video = CompositeVideoClip([
        VideoFileClip(input_file_path), 
        subtitles_stroke_black.set_position(("center", 1-subtitle_height), relative=True), 
        subtitles.set_position(("center", 1-subtitle_height), relative=True),
        ] + emoji_clips)
    
    # Fourth step: combine the intro audio with the tiktok audio
    new_audio = AudioFileClip("temp//temp_intro.mp3")
    existing_audio = audio_fadein(video.audio, new_audio.duration * 2)
    combined_audio = CompositeAudioClip([existing_audio, new_audio])
    video = video.set_audio(combined_audio)

    # Fifth step: generate outro audio and srt
    tts(video_outro, ai_voice, "temp//temp_outro.mp3")

    new_audio = AudioFileClip("temp//temp_outro.mp3")
    outro_start_time = round(video.duration-new_audio.duration, 2)

    i = 0
    model = whisper.load_model("base")
    transcribe = model.transcribe(audio="temp//temp_outro.mp3", word_timestamps=True, language="en")
    for segment in transcribe['segments']:
        for word in segment['words']:

            i += 1
            text = word["word"]
            start_time = outro_start_time + word["start"]
            end_time = outro_start_time + word["end"]
            word = f"{i}\n{util_format_time(start_time)} --> {util_format_time(end_time) }\n{text[1:] if text[0] == ' ' else text}\n\n"
            with open("temp//temp_outro.srt", "a", encoding="utf-8") as f: f.write(word)

    util_enhance_srt("temp//temp_outro.srt") # Remove punctuation marks and randomize capitalization


    # Sixth step: add outro subtitles to the video
    subtitles_stroke_black, subtitles = util_subtitle_compiler("temp//temp_outro.srt", "LawnGreen")
    subtitle_height = 0.75 # 75% of the video height

    video = CompositeVideoClip([
        video, 
        subtitles_stroke_black.set_position(("center", 1-subtitle_height), relative=True), 
        subtitles.set_position(("center", 1-subtitle_height), relative=True)
        ])

    # Seventh step: add outro audio to the video
    new_audio = new_audio.set_start(outro_start_time)
    existing_audio = audio_fadeout(video.audio, new_audio.duration * 2)
    combined_audio = CompositeAudioClip([existing_audio, new_audio])
    video = video.set_audio(combined_audio)

    # Eigth step: write the video to the output file
    video.write_videofile(output_file_path, codec="libx264")


def generate_tiktok_with_speech(input_file_path, output_file_path, video_intro, video_outro, ai_voice):

    # First step: extract audio from the downloaded tiktok video
    VideoFileClip(input_file_path).audio.write_audiofile("temp//temp.mp3")

    # Second step: generate captions from the extracted audio
    i = 0
    model = whisper.load_model("base")
    transcribe = model.transcribe(audio="temp//temp.mp3", word_timestamps=True, language="en")
    with open("temp//temp.srt", "w", encoding="utf-8") as f: pass # Generate empty file first as it might be that there are no words in the video
    for segment in transcribe['segments']:
        for word in segment['words']:

            i += 1
            text = word["word"]
            word = f"{i}\n{util_format_time(word["start"])} --> {util_format_time(word["end"]) }\n{text[1:] if text[0] == ' ' else text}\n\n"
            with open("temp//temp.srt", "a", encoding="utf-8") as f: f.write(word)

    util_enhance_srt("temp//temp.srt") # Remove punctuation marks and randomize capitalization

    if os.path.getsize("temp//temp.srt") == 0: 
        print("No words in the video, using intro captions instead.")
        generate_tiktok_without_speech(input_file_path, output_file_path, video_intro, video_outro, ai_voice)

    # Third step: add the captions to the video
    subtitles_stroke_black, subtitles = util_subtitle_compiler("temp//temp.srt", "Yellow")
    subtitle_height = 0.25 # 25% of the video height

    video = CompositeVideoClip([
        VideoFileClip(input_file_path), 
        subtitles_stroke_black.set_position(("center", 1-subtitle_height), relative=True), 
        subtitles.set_position(("center", 1-subtitle_height), relative=True)
        ])


    # Fourth step: generate and add intro audio to the video
    tts(video_intro, ai_voice, "temp//temp_intro.mp3")

    new_audio = AudioFileClip("temp//temp_intro.mp3")
    existing_audio = audio_fadein(video.audio, new_audio.duration * 2)
    combined_audio = CompositeAudioClip([existing_audio, new_audio])
    video = video.set_audio(combined_audio)

    # Fifth step: generate outro audio and srt
    tts(video_outro, ai_voice, "temp//temp_outro.mp3")

    new_audio = AudioFileClip("temp//temp_outro.mp3")
    outro_start_time = round(video.duration-new_audio.duration, 2)

    i = 0
    model = whisper.load_model("base")
    transcribe = model.transcribe(audio="temp//temp_outro.mp3", word_timestamps=True, language="en")
    for segment in transcribe['segments']:
        for word in segment['words']:

            i += 1
            text = word["word"]
            start_time = outro_start_time + word["start"]
            end_time = outro_start_time + word["end"]
            word = f"{i}\n{util_format_time(start_time)} --> {util_format_time(end_time) }\n{text[1:] if text[0] == ' ' else text}\n\n"
            with open("temp//temp_outro.srt", "a", encoding="utf-8") as f: f.write(word)

    util_enhance_srt("temp//temp_outro.srt") # Remove punctuation marks and randomize capitalization


    # Sixth step: add outro subtitles to the video
    subtitles_stroke_black, subtitles = util_subtitle_compiler("temp//temp_outro.srt", "LawnGreen")
    subtitle_height = 0.75 # 75% of the video height

    video = CompositeVideoClip([
        video, 
        subtitles_stroke_black.set_position(("center", 1-subtitle_height), relative=True), 
        subtitles.set_position(("center", 1-subtitle_height), relative=True)
        ])
    
    # Seventh step: add outro audio to the video
    new_audio = new_audio.set_start(outro_start_time)
    existing_audio = audio_fadeout(video.audio, new_audio.duration * 2)
    combined_audio = CompositeAudioClip([existing_audio, new_audio])
    video = video.set_audio(combined_audio)

    # Eigth step: write the video to the output file
    video.write_videofile(output_file_path, codec="libx264")



def generate_captions(session_groq, raw_description, topic):

    context = f"""
Instructions:
- Strictly follow the request.
- Do not greet. Do not add explanations.
- Give only the requested information, nothing else.
"""

    prompt = [{"role": "system", "content": context}, {"role": "user", "content": f"This is description under a tiktok video, tell me what is most likely to be going on there: {raw_description}"}]
    response = session_groq.chat.completions.create(model = "llama3-70b-8192", messages = prompt, stream = False, temperature = 0, max_tokens = 2048, stop = '"[end]"', top_p = 1)

    prompt = [{"role": "system", "content": context}, {"role": "user", "content": f"Generate the text for this tiktok as if you are a 10 year old cringe kid, no hashtags, no future tense, max three sentences: {response.choices[0].message.content}"}]
    response = session_groq.chat.completions.create(model = "llama3-70b-8192", messages = prompt, stream = False, temperature = 0, max_tokens = 2048, stop = '"[end]"', top_p = 1)
    video_intro = response.choices[0].message.content

    prompt = [{"role": "system", "content": context}, {"role": "user", "content": "Rephrase and add more relevant hashtags, up to 15 hashtags: " + raw_description}]
    response = session_groq.chat.completions.create(model = "llama3-70b-8192", messages = prompt, stream = False, temperature = 0, max_tokens = 2048, stop = '"[end]"', top_p = 1)
    video_description = response.choices[0].message.content

    return video_intro, video_description


if __name__ == '__main__':

    token_telegram = '7522802195:AAGZQptOGdKDAkiY79t_nX8lfBViOFSLdlI'
    url = f"https://api.telegram.org/bot{token_telegram}"

    count = 5

    list_ai_voices = [
        Voice.US_FEMALE_2,
        Voice.US_FEMALE_1,
        # Voice.US_MALE_1,
        # Voice.DE_MALE
    ]

    session_groq = Groq(api_key = "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")

    list_video_outros = [
        "Hit that like button and subscribe for more based content!",
        "Smash that like button and subscribe for more awesome content!",
        "Don’t forget to hit like and subscribe for more epic updates!",
        "Tap that like button and subscribe for more cool stuff!",
        "Click like and subscribe to stay updated with more great content!",
        "Hit the like button and subscribe for more awesome videos!",
        "Drop a like and subscribe for more top-tier content!",
        "Hit like, subscribe, and stay tuned for more great content!",
        "Show some love by liking and subscribing for more fun videos!",
        "Smash the like button and hit subscribe for more amazing content!"
    ]


    # Reading the config file with users and their interests
    with open('config.json', 'r') as f: config = json.load(f)

    for id in config:
        for topic in config[id]['topics']:

            print(f"Processing {topic.upper()} topic for {id}...")
            response = requests.post(url + "/sendMessage", data={'chat_id': id, 'protect_content': 'false', 'text': f"Incoming {topic.upper()} videos."})

            shutil.rmtree('./input')
            os.mkdir('./input')
            asyncio.run(download_tiktoks(count, topic))

            # Reading the metadata for the downloaded videos
            metadata = json.load(open("input//metadata.json"))
            videos_info = {video_dict['id']: video_dict['desc'] for video_dict in metadata}

            shutil.rmtree('./output')
            os.mkdir('./output')

            for file in os.listdir("input"):
                if file.endswith(".mp4"):

                    shutil.rmtree('./temp')
                    os.mkdir('./temp')

                    raw_description = videos_info.get(file.split(".")[0])
                    video_intro, video_description = generate_captions(session_groq, raw_description, topic)

                    # generate_tiktok_with_speech("input//"+file, "output//"+file, video_intro, random.choice(list_video_outros), random.choice(list_ai_voices))
                    generate_tiktok_without_speech("input//"+file, "output//"+file, video_intro, random.choice(list_video_outros), random.choice(list_ai_voices))

                    with open("output//"+file, 'rb') as video_file: response = requests.post(url + "/sendVideo", files={'video': video_file}, data={'chat_id': id, 'protect_content': 'false', 'caption': video_description})

                    # sys.exit()