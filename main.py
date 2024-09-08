from moviepy.audio.fx.audio_fadeout import audio_fadeout
from moviepy.audio.fx.audio_fadein import audio_fadein
from moviepy.video.tools.subtitles import SubtitlesClip
from util_downloader.tiktok_downloader import download_tiktoks
from moviepy.editor import VideoFileClip, CompositeVideoClip, TextClip, AudioFileClip, CompositeAudioClip, ImageClip, VideoClip
from moviepy.config import change_settings
from datetime import timedelta
from util_voice import Voice, tts
from pilmoji import Pilmoji
from emoji import UNICODE_EMOJI_ENGLISH
from groq import Groq
from PIL import ImageFont, Image

from pilmoji.source import AppleEmojiSource, GoogleEmojiSource, FacebookEmojiSource

import numpy as np

import requests
import asyncio
import whisper
import random
import shutil
import json
import ast
import sys
import os
import re


# Needed for caption generation
change_settings({"IMAGEMAGICK_BINARY": r"C:\\Program Files\\ImageMagick-7.1.1-Q16-HDRI\\magick.exe"})


# This class creates an animation for words to bounce
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


# Util for converting a timestamp to seconds
def util_convert_to_seconds(timestamp):
    hours, minutes, seconds = timestamp.replace(',', '.').split(':')
    total_seconds = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    return total_seconds


# Util for generating captions
def util_generate_captions(session_groq, raw_description, personality):

    context = f"""
Instructions:
- Strictly follow the request.
- Do not greet. Do not add explanations.
- Give only the requested information, nothing else.
"""
    
    if (personality == "billionaire"):
        prompt = [{"role": "system", "content": context}, {"role": "user", "content": f"Generate a random viral one-sentence short saying for success"}]
        response = session_groq.chat.completions.create(model = "llama3-70b-8192", messages = prompt, stream = False, temperature = 0.5, max_tokens = 2048, stop = '"[end]"', top_p = 1)
        video_intro = response.choices[0].message.content

    else:
        prompt = [{"role": "system", "content": context}, {"role": "user", "content": f"This is description under a tiktok video, tell me what is most likely to be going on there: {raw_description}"}]
        response = session_groq.chat.completions.create(model = "llama3-70b-8192", messages = prompt, stream = False, temperature = 0, max_tokens = 2048, stop = '"[end]"', top_p = 1)

        prompt = [{"role": "system", "content": context}, {"role": "user", "content": f"Generate the text for this tiktok as if you are a {personality}, no hashtags, no future tense, max two sentences: {response.choices[0].message.content}"}]
        response = session_groq.chat.completions.create(model = "llama3-70b-8192", messages = prompt, stream = False, temperature = 0, max_tokens = 2048, stop = '"[end]"', top_p = 1)
        video_intro = response.choices[0].message.content

    prompt = [{"role": "system", "content": context}, {"role": "user", "content": f"Generate a clickbait title for this tiktok as if you are a {personality}, no hashtags, max seven words: {response.choices[0].message.content}"}]
    response = session_groq.chat.completions.create(model = "llama3-70b-8192", messages = prompt, stream = False, temperature = 0, max_tokens = 2048, stop = '"[end]"', top_p = 1)
    video_title = response.choices[0].message.content

    video_intro = video_title + ". " + video_intro # appending clickbait title to get 3 second rule

    prompt = [{"role": "system", "content": context}, {"role": "user", "content": "Generate 3 most relevant hashtags based on this description: " + raw_description}]
    response = session_groq.chat.completions.create(model = "llama3-70b-8192", messages = prompt, stream = False, temperature = 0, max_tokens = 2048, stop = '"[end]"', top_p = 1)
    video_description = response.choices[0].message.content

    return video_intro, video_title, video_description


# Util for enhancing srt by removing punctuation marks and randomizing capitalization
def util_enhance_srt(srt_path):

    with open(srt_path, "r", encoding="utf-8") as f: lines = f.readlines()
    
    enhanced_lines = []
    for line in lines:
        if line.strip() and not bool(re.match(r'^\d+', line.strip())): # Only process non-empty lines that do not start with an integer
            line = line.replace('.', '').replace(',', '')
            if random.random() < 0.25: # 25% chance to capitalize a line
                line = line.upper()

        enhanced_lines.append(line)

    with open(srt_path, "w", encoding="utf-8") as f: f.writelines(enhanced_lines)


# Util that generates clips from srt
def util_subtitle_compiler(srt_path, color):

    # Create an instance of WordBouncer
    bouncer = UtilBouncer()

    method = "caption"
    font = "Impact"
    fontsize = 240
    align = "center"

    subtitles_stroke_black = SubtitlesClip(srt_path, lambda txt: TextClip(txt, method=method, font=font, fontsize=fontsize, align=align, color="black", stroke_width=24, stroke_color="black").set_duration(.3).resize(lambda t : bouncer.bounce(t, txt)))
    subtitles = SubtitlesClip(srt_path, lambda txt: TextClip(txt, method=method, font=font, fontsize=fontsize, align=align, color=color).set_duration(.3).resize(lambda t : bouncer.bounce(t, txt)))

    return subtitles_stroke_black, subtitles


# Util for word extraction from an srt in a list form
def util_word_list_from_srt(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
        text_parts = re.findall(r'\d+\n(?:\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}\n)?(.+?)(?:\n\n|\Z)', content, re.DOTALL)
        text = ' '.join(text_parts).replace("'", "").replace("`", "")
        list_words = re.findall(r'\b\w+\b', text)
        
    return list_words


# Util for generating emoji list from a word list
def util_generate_emoji_list_from_word_list(list_words):

    # Splitting the list of words into chunks. This increases the amount of api calls, but reduces the probability of a botched llm output.
    chunk_size = 8
    list_chunks = [list_words[x:x+chunk_size] for x in range(0, len(list_words), chunk_size)]

    emoji_list = []
    for chunk in list_chunks:

        for i in range(5):
                
            try:

                prompt = [
                    {
                        "role": "system", 
                        "content": f"""You are an asssitant that can only return python lists of emoji, nothing else. No symbols, no glyphs, only lists of emojis."""
                    },
                    {
                        "role": "user", 
                        "content": f"""Return a python list of emojis that are the most closely associated with each word within the list, nothing else. The word list is: {chunk}"""
                    }]

                response = session_groq.chat.completions.create(model = "llama-3.1-8b-instant", messages = prompt, stream = False, temperature = .5, max_tokens = 128, stop = '"[end]"', top_p = 1)
                list_emoji_chunk = response.choices[0].message.content

                for emoji in ast.literal_eval(list_emoji_chunk): emoji_list.append(emoji) # Generating a list of emojis from literal string outputs
                break

            except:
                print(f"Failed to generate list of emojis. Retrying {i}/5 time(s).")

    for emoji, word in zip(emoji_list, list_words): print(f"{emoji} - {word}") # Debugging tool
    emoji_list = emoji_list[:len(list_words)]
    return emoji_list


# Util for generating emoji sprinkle clips (the ones that randomly pop up)
def util_generate_emoji_sprinkle_clips(video_duration):

    list_emoji_sources = [AppleEmojiSource, GoogleEmojiSource, FacebookEmojiSource]

    emoji_set = random.choice([ # I guess might be better to prompt the llm for the list of most likely used emojis for the specific video.
        ["😤", "😂", "😍", "😎", "😢", "😡"],
        ["😊", "😂", "🤔", "🤢", "🤮", "🥵"],
        ["🤯", "😩", "😍", "😎", "💀", "😡"],
        ["🤯", "🤑", "😍", "🤢", "💀", "🤩"]
    ])

    clips = []
    for _ in range(int(video_duration/2)):

        clip_duration = random.randint(2, 6)/10
        source = random.choice(list_emoji_sources)

        # Create the emoji image from the character
        with Image.new("RGBA", (200, 200), (0, 0, 0, 0)) as image:
            with Pilmoji(image, source=source) as pilmoji:
                pilmoji.text((0, 0), random.choice(emoji_set).strip(), (0, 0, 0), emoji_font, emoji_scale_factor=random.randint(3, 8)/10)
        emoji_clip = ImageClip(np.array(image), duration=clip_duration)

        # Random start time within the video duration
        start_time = random.uniform(0, video_duration - clip_duration)
        
        # Random position within the video frame
        pos_x = random.choice([0.1, 0.8])
        pos_y = random.uniform(0.75, 0.85)
        
        # Set start time and position
        emoji_clip = emoji_clip.set_start(start_time).set_position((pos_x, pos_y), relative=True)
        
        clips.append(emoji_clip)
    
    return clips


# Util for generating emoji intro clips
def util_generate_emoji_intro_clips(emoji_list):

    source = AppleEmojiSource

    # Extracting the list of timestamps on when the emojis should pop up
    with open("temp//temp.srt", "r") as f: data = f.read()
    timestamp_list = re.compile(r"(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})").findall(data)

    clips = []
    for i in range(len(emoji_list)):

        # Calculating start and end times of the clip
        start_seconds = util_convert_to_seconds(timestamp_list[i][0])
        end_seconds = util_convert_to_seconds(timestamp_list[i][1])
        clip_duration = end_seconds - start_seconds

        if emoji_list[i].strip() == '': continue # Checking if the emoji is an empty string. Sometimes happens.
        if emoji_list[i] not in UNICODE_EMOJI_ENGLISH: continue # Checking if the emoji is not in the list of emojis. Sometimes happens.

        # Create the emoji image from the character
        with Image.new("RGBA", (200, 200), (0, 0, 0, 0)) as image:
            with Pilmoji(image, source=source) as pilmoji:

                pilmoji.text((0, 0), emoji_list[i].strip(), (0, 0, 0), emoji_font, emoji_scale_factor=.5)
        emoji_clip = ImageClip(np.array(image), duration=clip_duration).set_start(start_seconds).set_position((0.43, 0.65), relative=True)

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

    list_words = util_word_list_from_srt('temp/temp.srt')
    emoji_list = util_generate_emoji_list_from_word_list(list_words)
    emoji_clips_intro = util_generate_emoji_intro_clips(emoji_list)
    emoji_clips_sprinkle = util_generate_emoji_sprinkle_clips(video_duration=VideoFileClip(input_file_path).duration)

    video = CompositeVideoClip([
        VideoFileClip(input_file_path), 
        subtitles_stroke_black.set_position(("center", 1-subtitle_height), relative=True), 
        subtitles.set_position(("center", 1-subtitle_height), relative=True),
        ] + emoji_clips_intro + emoji_clips_sprinkle)
    
    # Fourth step: combine the intro audio with the tiktok audio
    new_audio = AudioFileClip("temp//temp_intro.mp3")
    intro_audio = new_audio
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

    # video = CompositeVideoClip([
    #     video, 
    #     subtitles_stroke_black.set_position(("center", 1-subtitle_height), relative=True), 
    #     subtitles.set_position(("center", 1-subtitle_height), relative=True)
    #     ])

    # Seventh step: add outro audio to the video
    new_audio = new_audio.set_start(outro_start_time)
    existing_audio = audio_fadeout(video.audio, new_audio.duration * 2)
    combined_audio = CompositeAudioClip([existing_audio, new_audio])
    # only_tts_audio = CompositeAudioClip([intro_audio, new_audio])
    # only_tts_audio.write_audiofile(output_file_path+".mp3")
    video = video.set_audio(combined_audio)

    # Eigth step: write the video to the output file
    video.write_videofile(output_file_path, codec = "libx264", logger = 'bar', threads=8)


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


# Running main
if __name__ == '__main__':

    test = True

    token_telegram = '7522802195:AAGZQptOGdKDAkiY79t_nX8lfBViOFSLdlI'
    url = f"https://api.telegram.org/bot{token_telegram}"

    emoji_font = ImageFont.truetype("data//arial.ttf", 192)

    clip_count = 3

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
    if test: 
        with open('config_test.json', 'r') as f: config = json.load(f)
    else: 
        with open('config.json', 'r') as f: config = json.load(f)

    for id in config["users"]:
        for topic in config["users"][id]['topics']:

            if not test:
                print(f"Processing {topic.upper()} topic for {id}...")
                response = requests.post(url + "/sendMessage", data={'chat_id': id, 'protect_content': 'false', 'text': f"Incoming {topic.upper()} videos."})

                shutil.rmtree('./input')
                os.mkdir('./input')
                asyncio.run(download_tiktoks(clip_count, topic))

            # Reading the metadata for the downloaded videos
            metadata = json.load(open("input//metadata.json"))
            videos_info = {video_dict['id']: video_dict['desc'] for video_dict in metadata}

            shutil.rmtree('./output')
            os.mkdir('./output')

            for file in os.listdir("input"):
                if file.endswith(".mp4"):

                    shutil.rmtree('./temp')
                    os.mkdir('./temp')

                    personality = config["personalities"][topic]
                    raw_description = videos_info.get(file.split(".")[0])
                    video_intro, video_title, video_description = util_generate_captions(session_groq, raw_description, personality)

                    if personality == 'billionaire': ai_voice = Voice.MALE_SANTA_NARRATION
                    else: ai_voice = random.choice(list_ai_voices)

                    # generate_tiktok_with_speech("input//"+file, "output//"+file, video_intro, random.choice(list_video_outros), random.choice(list_ai_voices))
                    generate_tiktok_without_speech("input//"+file, "output//"+file, video_intro, random.choice(list_video_outros), ai_voice)

                    if not test:
                        with open("output//"+file, 'rb') as video_file: response = requests.post(url + "/sendVideo", files={'video': video_file}, data={'chat_id': id, 'protect_content': 'false', 'caption': f"{video_title}\n\n{video_description}"})

                    if test:
                        sys.exit()