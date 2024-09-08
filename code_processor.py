from moviepy.audio.fx.audio_fadeout import audio_fadeout
from moviepy.audio.fx.audio_fadein import audio_fadein
from moviepy.video.tools.subtitles import SubtitlesClip
from tiktok_downloader import download_tiktoks
from moviepy.editor import VideoFileClip, CompositeVideoClip, TextClip, AudioFileClip, CompositeAudioClip, ImageClip, VideoClip
from moviepy.config import change_settings
from util_voice import Voice
from util_voice import tts as util_text_to_speech
from datetime import timedelta
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

def util_format_time(seconds: float) -> str:
    """Formats time in seconds to SRT format hh:mm:ss,SSS."""
    td = timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    milliseconds = int(td.microseconds / 1000)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"

def util_llm(prompt):
    context_groq = f"Instructions:\n- Strictly follow the request.\n- Do not greet. Do not add explanations.\n- Give only the requested information, nothing else."
    prompt = [{"role": "system", "content": context_groq}, {"role": "user", "content": prompt}]
    response = session_groq.chat.completions.create(model = "llama3-70b-8192", messages = prompt, stream = False, temperature = 0, max_tokens = 2048, stop = '"[end]"', top_p = 1)
    return response.choices[0].message.content

def util_speech_to_srt(input_file_path, output_file_path):

    i = 0
    model = whisper.load_model("base")
    transcribe = model.transcribe(audio=input_file_path, word_timestamps=True, language="en")
    for segment in transcribe['segments']:
        for word in segment['words']:
            i += 1
            text = word["word"]
            word = f"{i}\n{util_format_time(word["start"])} --> {util_format_time(word["end"]) }\n{text[1:] if text[0] == ' ' else text}\n\n"
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


def util_srt_to_subtitles(input_file_path):

    




def generate_explanation(raw_video_description):
    video_explanation = util_llm(f"This is description under a tiktok video, tell me what is most likely to be going on there: {raw_video_description}")
    print("Video explanation: ", video_explanation)
    return video_explanation


def generate_title(video_explanation, personality):
    video_title = util_llm(f"Generate a clickbait title for this tiktok as if you are a {personality}, no hashtags, max seven words: {video_explanation}")
    print("Video title: ", video_title)
    return video_title


def generate_intro(video_explanation, video_id, voice, personality, video_title, raw_video_description):
    if (personality == "billionaire"): video_intro = util_llm(f"Generate a random viral one-sentence short saying for success")
    else: video_intro = util_llm(f"Generate the text for this tiktok as if you are a {personality}, no hashtags, no future tense, max two sentences: {video_explanation}")
    video_intro = video_title + ". " + video_intro # appending clickbait title to get 3 second rule
    print("Video intro: ", video_intro)

    util_text_to_speech(video_intro, voice, "temp//intro.mp3")
    util_speech_to_srt("temp//intro.mp3", "temp//intro.srt")

    video_intro_subtitles = util_srt_to_subtitles("temp//intro.srt")


    pass


def generate_outro(video_id, voice):
    pass



def generate_video():
    pass


def generate_description(video_explanation):
    video_description = util_llm("Generate 3 most relevant hashtags based on this description: " + video_explanation)
    print("Video description: ", video_description)
    return video_description



if __name__ == "__main__":

    list_video_ids = ["7312381832148864262"]

    with open("input/json_metadata.json", "r") as file: json_metadata = json.load(file)
    with open("json_config.json", "r") as file: json_config = json.load(file)
    session_groq = Groq(api_key = "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")    

    for video_id in list_video_ids:

        shutil.rmtree('./temp')
        os.mkdir('./temp')

        personality = json_config['characters'][json_metadata[video_id]["topic"]]
        if personality in ["billionaire"]: voice = Voice.MALE_SANTA_NARRATION
        else: voice = random.choice([Voice.US_FEMALE_1, Voice.US_FEMALE_2])

        video_explanation = generate_explanation(json_metadata[video_id]["desc"])
        video_title = generate_title(video_explanation, personality)
        video_intro = generate_intro(video_explanation, video_id, voice, personality, video_title, json_metadata[video_id]["desc"])
        video_outro = generate_outro(video_id, voice)
        video_description = generate_description(video_explanation)

        generate_video(video_intro, video_outro)