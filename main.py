



from moviepy.video.tools.subtitles import SubtitlesClip

from moviepy.audio.fx.audio_fadein import audio_fadein
from moviepy.audio.fx.audio_fadeout import audio_fadeout
from moviepy.editor import VideoFileClip, CompositeVideoClip, TextClip, AudioFileClip, CompositeAudioClip
from moviepy.config import change_settings
from datetime import timedelta
from tt_voice import Voice, tts

import whisper
import shutil
import os

shutil.rmtree('./temp')
os.mkdir('./temp')

change_settings({"IMAGEMAGICK_BINARY": r"C:\\Program Files\\ImageMagick-7.1.1-Q16-HDRI\\magick.exe"})

# Util for accurate caption file generation
def format_time(seconds: float) -> str:
    """Formats time in seconds to SRT format hh:mm:ss,SSS."""
    td = timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    milliseconds = int(td.microseconds / 1000)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"





def download_video(topic):
    pass



def generate_tiktok_without_speech(input_file_path, output_file_path, topic_intro, topic_outro, ai_voice):

    # First step: generate intro audio
    tts(topic_intro, ai_voice, "temp//temp_intro.mp3")

    # Second step: generate captions from the generated intro audio
    i = 0
    model = whisper.load_model("base")
    transcribe = model.transcribe(audio="temp//temp_intro.mp3", word_timestamps=True, language="en")
    for segment in transcribe['segments']:
        for word in segment['words']:

            i += 1
            text = word["word"]
            word = f"{i}\n{format_time(word["start"])} --> {format_time(word["end"]) }\n{text[1:] if text[0] == ' ' else text}\n\n"
            with open("temp//temp.srt", "a", encoding="utf-8") as f: f.write(word)

    # Third step: add the captions to the video
    method = "caption"
    font = "Comic-Sans-MS-Bold"
    fontsize = 80
    align = "center"

    subtitles_stroke_black = SubtitlesClip("temp//temp.srt", lambda txt: TextClip(txt, method=method, font=font, fontsize=fontsize, align=align, stroke_width=12, stroke_color="black"))
    subtitles_stroke_white = SubtitlesClip("temp//temp.srt", lambda txt: TextClip(txt, method=method, font=font, fontsize=fontsize, align=align, stroke_width=3, stroke_color="white"))
    subtitles = SubtitlesClip("temp//temp.srt", lambda txt: TextClip(txt, method=method, font=font, fontsize=fontsize, align=align, color="yellow"))

    subtitle_height = 0.25 # 25% of the video height

    video = CompositeVideoClip([
        VideoFileClip(input_file_path), 
        subtitles_stroke_black.set_position(("center", 1-subtitle_height), relative=True), 
        subtitles_stroke_white.set_position(("center", 1-subtitle_height), relative=True), 
        subtitles.set_position(("center", 1-subtitle_height), relative=True)
        ])
    
    # Fourth step: combine the intro audio with the tiktok audio
    new_audio = AudioFileClip("temp//temp_intro.mp3")
    existing_audio = audio_fadein(video.audio, new_audio.duration * 2)
    combined_audio = CompositeAudioClip([existing_audio, new_audio])
    video = video.set_audio(combined_audio)

    # Fifth step: generate outro audio and srt
    tts(topic_outro, ai_voice, "temp//temp_outro.mp3")

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
            word = f"{i}\n{format_time(start_time)} --> {format_time(end_time) }\n{text[1:] if text[0] == ' ' else text}\n\n"
            with open("temp//temp_outro.srt", "a", encoding="utf-8") as f: f.write(word)


    # Sixth step: add outro subtitles to the video
    subtitles_stroke_black = SubtitlesClip("temp//temp_outro.srt", lambda txt: TextClip(txt, method=method, font=font, fontsize=fontsize, align=align, stroke_width=12, stroke_color="black"))
    subtitles_stroke_white = SubtitlesClip("temp//temp_outro.srt", lambda txt: TextClip(txt, method=method, font=font, fontsize=fontsize, align=align, stroke_width=3, stroke_color="white"))
    subtitles = SubtitlesClip("temp//temp_outro.srt", lambda txt: TextClip(txt, method=method, font=font, fontsize=fontsize, align=align, color="green"))

    subtitle_height = 0.75 # 75% of the video height

    video = CompositeVideoClip([
        video, 
        subtitles_stroke_black.set_position(("center", 1-subtitle_height), relative=True), 
        subtitles_stroke_white.set_position(("center", 1-subtitle_height), relative=True),  
        subtitles.set_position(("center", 1-subtitle_height), relative=True)
        ])

    # Seventh step: add outro audio to the video
    new_audio = new_audio.set_start(outro_start_time)
    existing_audio = audio_fadeout(video.audio, new_audio.duration * 2)
    combined_audio = CompositeAudioClip([existing_audio, new_audio])
    video = video.set_audio(combined_audio)

    # Eigth step: write the video to the output file
    video.write_videofile(output_file_path, codec="libx264")




def generate_tiktok_with_speech(input_file_path, output_file_path, topic_intro, topic_outro, ai_voice):

    # First step: extract audio from the downloaded tiktok video
    VideoFileClip(input_file_path).audio.write_audiofile("temp//temp.mp3")

    # Second step: generate captions from the extracted audio
    i = 0
    model = whisper.load_model("base")
    transcribe = model.transcribe(audio="temp//temp.mp3", word_timestamps=True, language="en")
    for segment in transcribe['segments']:
        for word in segment['words']:

            i += 1
            text = word["word"]
            word = f"{i}\n{format_time(word["start"])} --> {format_time(word["end"]) }\n{text[1:] if text[0] == ' ' else text}\n\n"
            with open("temp//temp.srt", "a", encoding="utf-8") as f: f.write(word)

    # Third step: add the captions to the video
    method = "caption"
    font = "Comic-Sans-MS-Bold"
    fontsize = 80
    align = "center"

    subtitles_stroke_black = SubtitlesClip("temp//temp.srt", lambda txt: TextClip(txt, method=method, font=font, fontsize=fontsize, align=align, stroke_width=12, stroke_color="black"))
    subtitles_stroke_white = SubtitlesClip("temp//temp.srt", lambda txt: TextClip(txt, method=method, font=font, fontsize=fontsize, align=align, stroke_width=3, stroke_color="white"))
    subtitles = SubtitlesClip("temp//temp.srt", lambda txt: TextClip(txt, method=method, font=font, fontsize=fontsize, align=align, color="yellow"))

    subtitle_height = 0.25 # 25% of the video height

    video = CompositeVideoClip([
        VideoFileClip("input.mp4"), 
        subtitles_stroke_black.set_position(("center", 1-subtitle_height), relative=True), 
        subtitles_stroke_white.set_position(("center", 1-subtitle_height), relative=True),  
        subtitles.set_position(("center", 1-subtitle_height), relative=True)
        ])

    # Fourth step: generate and add intro audio to the video
    tts(topic_intro, ai_voice, "temp//temp_intro.mp3")

    new_audio = AudioFileClip("temp//temp_intro.mp3")
    existing_audio = audio_fadein(video.audio, new_audio.duration * 2)
    combined_audio = CompositeAudioClip([existing_audio, new_audio])
    video = video.set_audio(combined_audio)



    # Fifth step: generate outro audio and srt
    tts(topic_outro, ai_voice, "temp//temp_outro.mp3")

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
            word = f"{i}\n{format_time(start_time)} --> {format_time(end_time) }\n{text[1:] if text[0] == ' ' else text}\n\n"
            with open("temp//temp_outro.srt", "a", encoding="utf-8") as f: f.write(word)


    # Sixth step: add outro subtitles to the video
    subtitles_stroke_black = SubtitlesClip("temp//temp_outro.srt", lambda txt: TextClip(txt, method=method, font=font, fontsize=fontsize, align=align, stroke_width=12, stroke_color="black"))
    subtitles_stroke_white = SubtitlesClip("temp//temp_outro.srt", lambda txt: TextClip(txt, method=method, font=font, fontsize=fontsize, align=align, stroke_width=3, stroke_color="white"))
    subtitles = SubtitlesClip("temp//temp_outro.srt", lambda txt: TextClip(txt, method=method, font=font, fontsize=fontsize, align=align, color="green"))

    subtitle_height = 0.75 # 75% of the video height

    video = CompositeVideoClip([
        video, 
        subtitles_stroke_black.set_position(("center", 1-subtitle_height), relative=True), 
        subtitles_stroke_white.set_position(("center", 1-subtitle_height), relative=True),  
        subtitles.set_position(("center", 1-subtitle_height), relative=True)
        ])
    
    # Seventh step: add outro audio to the video
    new_audio = new_audio.set_start(outro_start_time)
    existing_audio = audio_fadeout(video.audio, new_audio.duration * 2)
    combined_audio = CompositeAudioClip([existing_audio, new_audio])
    video = video.set_audio(combined_audio)

    # Eigth step: write the video to the output file
    video.write_videofile(output_file_path, codec="libx264")




ai_voice = Voice.UK_MALE_1
input_file_path = "input.mp4"
output_file_path = "output.mp4"
topic_intro = "I want a big beautiful black lady here in Detroit to fart in my mouth with gas."
topic_outro = "Hit that like button and subscribe for more based content!"

# generate_tiktok_without_speech(input_file_path, output_file_path, topic_intro, topic_outro)
generate_tiktok_with_speech(input_file_path, output_file_path, topic_intro, topic_outro, ai_voice)