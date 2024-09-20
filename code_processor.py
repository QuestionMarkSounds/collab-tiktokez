from moviepy.audio.fx.audio_fadeout import audio_fadeout
from moviepy.audio.fx.audio_fadein import audio_fadein
from moviepy.video.tools.subtitles import SubtitlesClip
from moviepy.editor import VideoFileClip, CompositeVideoClip, TextClip, AudioFileClip, CompositeAudioClip, ImageClip
from moviepy.config import change_settings
from util_text_to_speech import Voice
from util_text_to_speech import tts as util_text_to_speech
from datetime import timedelta
from pilmoji import Pilmoji
from emoji import UNICODE_EMOJI_ENGLISH
from groq import Groq
from PIL import ImageFont, Image

from pilmoji.source import AppleEmojiSource, GoogleEmojiSource, FacebookEmojiSource

import numpy as np

import requests
import whisper
import random
import shutil
import json
import ast
import sys
import os
import re


# Util class for bouncy text animation
class UtilBouncer:
    def __init__(self):
        self.previous_word = None
        self.time_elapsed = 0
        self.max_t = 0
        
        # Scaling factor to revert size changes
        self.scaling_factor = 200 / 80  # 3.125

        # Updated size ratios based on new font size
        self.small = 0.6 / self.scaling_factor
        self.medium = 1.0 / self.scaling_factor
        self.large = 1.1 / self.scaling_factor

    def bounce(self, t, txt):
        if self.max_t < t:
            self.max_t = t
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
                result = self.large - t * (self.large - self.medium)
            else:
                result = self.medium

        # Update the previous word to the current word
        self.previous_word = txt
        return result

# Util for converting seconds to SRT format
def util_format_time(seconds: float) -> str:
    """Formats time in seconds to SRT format hh:mm:ss,SSS."""
    td = timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    milliseconds = int(td.microseconds / 1000)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"

# Util for converting a timestamp to seconds
def util_convert_to_seconds(timestamp):
    hours, minutes, seconds = timestamp.replace(',', '.').split(':')
    total_seconds = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    return total_seconds

# Util for LLM prompts
def util_llm(prompt):
    context_groq = f"Instructions:\n- Strictly follow the request.\n- Do not greet. Do not add explanations.\n- Give only the requested information, nothing else."
    prompt = [{"role": "system", "content": context_groq}, {"role": "user", "content": prompt}]
    response = session_groq.chat.completions.create(model = "llama3-70b-8192", messages = prompt, stream = False, temperature = 0, max_tokens = 2048, stop = '"[end]"', top_p = 1)
    return response.choices[0].message.content

# Util that converts speech to srt
def util_speech_to_srt(input_file_path, output_file_path, clip_start_time):

    i = 0
    model = whisper.load_model("base")
    transcribe = model.transcribe(audio=input_file_path, word_timestamps=True, language="en")
    for segment in transcribe['segments']:
        for word in segment['words']:
            i += 1
            text = word["word"]
            start_time = clip_start_time + word["start"]
            end_time = clip_start_time + word["end"]
            word = f"{i}\n{util_format_time(start_time)} --> {util_format_time(end_time) }\n{text[1:] if text[0] == ' ' else text}\n\n"
            with open(output_file_path, "a", encoding="utf-8") as f: f.write(word)

    with open(output_file_path, "r", encoding="utf-8") as f: lines = f.readlines()
    enhanced_lines = []
    for line in lines:
        if line.strip() and not bool(re.match(r'^\d+', line.strip())): # Only process non-empty lines that do not start with an integer
            line = line.replace('.', '').replace(',', '')
            if random.random() < 0.25: # 25% chance to capitalize a line
                line = line.upper()

        enhanced_lines.append(line)
    with open(output_file_path, "w", encoding="utf-8") as f: f.writelines(enhanced_lines)

# Util that creates subtitles based on srt
def util_srt_to_subtitles(input_file_path, color):

    # Create an instance of WordBouncer
    bouncer = UtilBouncer()

    method = "caption"
    font = "Impact"
    fontsize = 240
    align = "center"

    video_subtitles_stroke = SubtitlesClip(input_file_path, lambda txt: TextClip(txt, method=method, font=font, fontsize=fontsize, align=align, color="black", stroke_width=24, stroke_color="black").set_duration(.3).resize(lambda t : bouncer.bounce(t, txt)))
    video_subtitles = SubtitlesClip(input_file_path, lambda txt: TextClip(txt, method=method, font=font, fontsize=fontsize, align=align, color=color).set_duration(.3).resize(lambda t : bouncer.bounce(t, txt)))

    return video_subtitles_stroke, video_subtitles

# Util that creates emojis based on srt
def util_srt_to_emojis(input_file_path):

    # Get list of words from the srt file
    with open(input_file_path, 'r', encoding='utf-8') as file:
        content = file.read()
        text_parts = re.findall(r'\d+\n(?:\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}\n)?(.+?)(?:\n\n|\Z)', content, re.DOTALL)
        text = ' '.join(text_parts).replace("'", "").replace("`", "")
        list_words = re.findall(r'\b\w+\b', text)
        list_timestamps = re.compile(r"(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})").findall(content)

    # Split the list in chunks for better prompting
    chunk_size = 8
    list_chunks = [list_words[x:x+chunk_size] for x in range(0, len(list_words), chunk_size)]

    list_emojis = []
    for chunk in list_chunks:
        for i in range(5):
            try:
                prompt = [
                    {"role": "system", "content": f"You are an asssitant that can only return python lists of emoji, nothing else. No symbols, no glyphs, only lists of emojis."},
                    {"role": "user", "content": f"Return a python list of emojis that are the most closely associated with each word within the list, nothing else. The word list is: {chunk}"}
                ]
            
                response = session_groq.chat.completions.create(model = "llama-3.1-8b-instant", messages = prompt, stream = False, temperature = .5, max_tokens = 128, stop = '"[end]"', top_p = 1)
                list_emoji_chunk = response.choices[0].message.content
                for emoji in ast.literal_eval(list_emoji_chunk): list_emojis.append(emoji) # Generating a list of emojis from literal string outputs
                break

            except: print(f"Failed to generate list of emojis. Retrying {i}/5 time(s).")

    # for emoji, word in zip(list_emojis, list_words): print(f"{emoji} - {word}") # Debugging tool
    list_emojis = list_emojis[:len(list_words)] # Sometimes the list of emojis is longer than the text list for some reason. FIX

    # Generate emoji clips
    emoji_source = AppleEmojiSource
    emoji_font = ImageFont.truetype("data//arial.ttf", 192)
    emoji_position = (0.415, 0.65)

    list_clips = []
    for i in range(len(list_emojis)):

        # Calculating start and end times of the clip
        start_seconds = util_convert_to_seconds(list_timestamps[i][0])
        end_seconds = util_convert_to_seconds(list_timestamps[i][1])
        clip_duration = end_seconds - start_seconds

        if list_emojis[i].strip() == '': continue # Checking if the emoji is an empty string. Sometimes happens.
        if list_emojis[i] not in UNICODE_EMOJI_ENGLISH: continue # Checking if the emoji is not in the list of emojis. Sometimes happens.

        # Create the emoji image from the character
        with Image.new("RGBA", (200, 200), (0, 0, 0, 0)) as image:
            with Pilmoji(image, source=emoji_source) as pilmoji:
                pilmoji.text((0, 0), list_emojis[i].strip(), (0, 0, 0), emoji_font, emoji_scale_factor=.5)
        emoji_clip = ImageClip(np.array(image), duration=clip_duration).set_start(start_seconds).set_position(emoji_position, relative=True)
        list_clips.append(emoji_clip)

    return list_clips

# Util that creates random emoji clips
def util_sprinkle_emojis(video_duration):

    list_emoji_sources = [AppleEmojiSource, GoogleEmojiSource, FacebookEmojiSource]
    emoji_font = ImageFont.truetype("data//arial.ttf", 192)
    emoji_set = random.choice([ # I guess might be better to prompt the llm for the list of most likely used emojis for the specific video.
        ["😤", "😂", "😍", "😎", "😢", "😡"],
        ["😊", "😂", "🤔", "🤢", "🤮", "🥵"],
        ["🤯", "😩", "😍", "😎", "💀", "😡"],
        ["🤯", "🤑", "😍", "🤢", "💀", "🤩"]
    ])

    list_clips = []
    for i in range(int(video_duration/2)):

        emoji_duration = random.randint(2, 6)/10
        emoji_position = (random.choice([0.1, 0.8]), random.uniform(0.75, 0.85))
        emoji_start_time = random.uniform(0, video_duration - emoji_duration)
        emoji_source = random.choice(list_emoji_sources)

        # Create the emoji image from the character
        with Image.new("RGBA", (200, 200), (0, 0, 0, 0)) as image:
            with Pilmoji(image, source=emoji_source) as pilmoji:
                pilmoji.text((0, 0), random.choice(emoji_set).strip(), (0, 0, 0), emoji_font, emoji_scale_factor=random.randint(3, 8)/10)
        emoji_clip = ImageClip(np.array(image), duration=emoji_duration)

        # Set start time and position
        emoji_clip = emoji_clip.set_start(emoji_start_time).set_position(emoji_position, relative=True)
        list_clips.append(emoji_clip)
    
    return list_clips

# Util that adds audio line to the video
def util_add_audio(path_mp3, video, type, start_time):

    audio_outro = AudioFileClip(path_mp3).set_start(start_time)
    if type == 'intro': audio_video_existing = audio_fadein(video.audio, audio_outro.duration * 2)
    elif type == 'outro': audio_video_existing = audio_fadeout(video.audio, audio_outro.duration * 2)
    audio_combined = CompositeAudioClip([audio_video_existing, audio_outro])
    video = video.set_audio(audio_combined)
    return video

# Generate explanation of what is going on in the video based on the raw description
def generate_explanation(file_path, raw_video_description):

    file_audio = VideoFileClip(file_path).audio
    file_audio.write_audiofile("temp//description.mp3")

    model = whisper.load_model("base")
    video_transcription = model.transcribe("temp//description.mp3", language="en")['text']

    video_explanation = util_llm(f"You are given audio transcription of a tiktok and a description, tell me what is most likely to be going on there: \nTranscription: {video_transcription}\nDescription: {raw_video_description}")
    print("Video explanation: ", video_explanation)
    return video_explanation

# Generate clickbait title for the video
def generate_title(video_explanation, personality):
    video_title = util_llm(f"Generate a short title for this tiktok as if you are a {personality}, no hashtags, max seven words: {video_explanation}")
    print("Video title: ", video_title)
    return video_title.replace('"', '').replace("'", '')

# Generate hashtags for the videos
def generate_description(video_explanation):
    video_description = util_llm("Generate 3 most relevant hashtags based on this description: " + video_explanation)
    print("Video description: ", video_description)
    return video_description.replace('"', '').replace("'", '')

# Adding intro to the video
def add_intro_to_video(file_path, video_explanation, video_id, voice, personality, video_title, raw_video_description):
    path_intro_mp3 = "temp//intro.mp3"
    subtitles_color = "yellow"
    subtitles_height = 0.25

    if (personality == "billionaire"): video_intro = util_llm(f"Generate a random viral one-sentence short saying for success")
    else: video_intro = util_llm(f"Generate the text for this tiktok as if you are a {personality}, no hashtags, no future tense, max two sentences: {video_explanation}")
    video_intro = video_title + ". " + video_intro # appending clickbait title to get 3 second rule
    print("Video intro: ", video_intro)

    util_text_to_speech(video_intro, voice, path_intro_mp3)
    util_speech_to_srt(path_intro_mp3, "temp//intro.srt", 0)

    # Get subtitle and emoji clips
    video_subtitles_stroke, video_subtitles = util_srt_to_subtitles("temp//intro.srt", subtitles_color)
    clips_subtitles_emojis = util_srt_to_emojis("temp//intro.srt")
    clips_sprinkle_emojis = util_sprinkle_emojis(VideoFileClip(file_path).duration)

    # Combine the video with subtitle and emoji clips
    video = CompositeVideoClip([
        VideoFileClip(file_path), 
        video_subtitles_stroke.set_position(("center", 1-subtitles_height), relative=True), 
        video_subtitles.set_position(("center", 1-subtitles_height), relative=True),
    ] + clips_subtitles_emojis + clips_sprinkle_emojis) # 

    # Combine the video with intro audio
    video = util_add_audio(path_intro_mp3, video, 'intro', 0)
    return video

# Adding outro to the video
def add_outro_to_video(video, video_id, voice):
    path_outro_mp3 = "temp//outro.mp3"
    subtitles_color = "lawngreen"
    subtitles_height = 0.65

    list_video_outros = [
        "Hit that like button and subscribe for more based content!",
        "Smash that like button and subscribe for more awesome content!",
        "Dont forget to hit like and subscribe for more epic updates!",
        "Tap that like button and subscribe for more cool stuff!",
        "Click like and subscribe to stay updated with more great content!",
        "Hit the like button and subscribe for more awesome videos!",
        "Drop a like and subscribe for more top-tier content!",
        "Hit like, subscribe, and stay tuned for more great content!",
        "Show some love by liking and subscribing for more fun videos!",
        "Smash the like button and hit subscribe for more amazing content!"
    ]
    video_outro = random.choice(list_video_outros)
    print("Video outro: ", video_outro)

    util_text_to_speech(video_outro, voice, path_outro_mp3)
    outro_start_time = round(video.duration-AudioFileClip(path_outro_mp3).duration, 2)
    util_speech_to_srt(path_outro_mp3, "temp//outro.srt", outro_start_time)

    # Get subtitle clips
    video_subtitles_stroke, video_subtitles = util_srt_to_subtitles("temp//outro.srt", subtitles_color)

    # Combine the video with subtitle clips
    video = CompositeVideoClip([
        video,
        video_subtitles_stroke.set_position(("center", 1-subtitles_height), relative=True), 
        video_subtitles.set_position(("center", 1-subtitles_height), relative=True)
    ])

    # Combine the video with outro audio
    video = util_add_audio(path_outro_mp3, video, 'outro', outro_start_time)
    return video

# Main
if __name__ == "__main__":

    shutil.rmtree('./output')
    os.mkdir('./output')

    list_video_ids = ["satisfying_4", "travel_1", "luxury_1"]

    # Settings init
    with open("json_metadata.json", "r") as file: json_metadata = json.load(file)
    with open("json_config_test.json", "r") as file: json_config = json.load(file)
    change_settings({"IMAGEMAGICK_BINARY": r"C:\\Program Files\\ImageMagick-7.1.1-Q16-HDRI\\magick.exe"})
    session_groq = Groq(api_key = "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")
    token_telegram = '7522802195:AAGZQptOGdKDAkiY79t_nX8lfBViOFSLdlI'
    url = f"https://api.telegram.org/bot{token_telegram}"  

    for video_id in list_video_ids:

        shutil.rmtree('./temp')
        os.mkdir('./temp')

        file_path = f"input//{video_id}.mp4"
        video_topic = video_id.split("_")[0]
        video_personality = json_config['characters'][video_topic]

        if video_personality in ["billionaire"]: voice = Voice.MALE_SANTA_NARRATION
        # else: voice = random.choice([Voice.US_FEMALE_1, Voice.US_FEMALE_2])
        else: voice = Voice.US_FEMALE_2

        video_explanation = generate_explanation(file_path, json_metadata[video_id])
        # video_explanation = "A 25 yo woman makeup asrm tutorial getting ready for a date"
        video_title = generate_title(video_explanation, video_personality)
        video_description = generate_description(video_explanation)
        

        video = add_intro_to_video(file_path, video_explanation, video_id, voice, video_personality, video_title, json_metadata[video_id])
        video = add_outro_to_video(video, video_id, voice)

        video.write_videofile(f"output//{video_id}.mp4", codec = "libx264", logger = 'bar', threads=8)

        # Getting chat ID
        for user in json_config["users"]:
            if video_topic in json_config["users"][user]["topics"]: 
                chat_id = user

        caption = f"{video_topic.upper()}\n\n{video_title}\n\n{video_description}"
        # with open(f"output//{video_id}.mp4", 'rb') as video_file: response = requests.post(url + "/sendVideo", files={'video': video_file}, data={'chat_id': chat_id, 'protect_content': 'false', 'caption': caption})
        with open(f"output//{video_id}.mp4", 'rb') as video_file: response = requests.post(url + "/sendVideo", files={'video': video_file}, data={'chat_id': "70476847", 'protect_content': 'false', 'caption': caption})
