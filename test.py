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

""
tts("Check tiktok downloader and make it download most recent tiktoks. within the metadata we can find the date of posting I think", Voice.MALE_SANTA_NARRATION, "temp//temp_test.mp3")