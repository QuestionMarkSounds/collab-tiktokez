from main import make_emoji_image
from pilmoji import Pilmoji
from groq import Groq
from PIL import ImageFont, Image

from moviepy.editor import VideoFileClip, CompositeVideoClip, TextClip, AudioFileClip, CompositeAudioClip, ImageClip
from moviepy.config import change_settings

import random
import re

def create_emoji_clips(emoji_list, timestamp_list):
    clips = []

    for i in range(len(emoji_list)):
        try:
            start_seconds = convert_to_seconds(timestamp_list[i][0])
            end_seconds = convert_to_seconds(timestamp_list[i][1])
            clip_duration = end_seconds - start_seconds
            emoji_image = make_emoji_image(emoji_list[i])
            
            # Create an ImageClip from the emoji image
            emoji_clip = ImageClip(emoji_image, duration=clip_duration)    
                    # Random position within the video frame
            pos_x = random.choice([0.1, 0.8])  # Relative positions from 0.1 to 0.9
            pos_y = random.uniform(0.75, 0.85)
            
            # Set start time and position
            emoji_clip = emoji_clip.set_start(start_seconds).set_position((pos_x, pos_y), relative=True)   
            clips.append(emoji_clip)
        except:
            pass
    return clips

def convert_to_seconds(timestamp):
    # Replace comma with dot for easier conversion
    timestamp = timestamp.replace(',', '.')
    
    # Split the timestamp into hours, minutes, seconds.milliseconds
    hours, minutes, seconds = timestamp.split(':')
    
    # Convert to seconds
    total_seconds = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    
    return total_seconds

def is_word(string):
    return any(char.isalpha() for char in string)

def extract_timestamps(srt_data):
    # Define a regex pattern to match the timestamps
    timestamp_pattern = re.compile(r"(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})")
    
    # Find all timestamps in the SRT data
    timestamps = timestamp_pattern.findall(srt_data)
    
    # Return the list of extracted timestamps
    return timestamps

def emojifier(session_groq, input_sentence):
    input_sentence = input_sentence.replace('.', '').replace(',', '')

    prompt = [
        {"role": "user", "content": f"""

        \n Insert face emoji after words from the sentence and at the end of the sentence that are likely to be associated with the word.  Do not return anything but the modified sentence.
        The sentence: {input_sentence}"""}]
    response = session_groq.chat.completions.create(model = "llama3-70b-8192", messages = prompt, stream = False, temperature = 0, max_tokens = 2048, stop = '"[end]"', top_p = 1)
    emojified_text = response.choices[0].message.content
    print("Emojified text: ",emojified_text)

    emoji_list = extract_and_duplicate_emojis(emojified_text)

    return emoji_list


def extract_and_duplicate_emojis(text):
    # Unicode ranges for emojis
    emoji_pattern = re.compile(
        r'[\U0001F600-\U0001F64F]'  # emoticons
        r'|[\U0001F300-\U0001F5FF]'  # symbols & pictographs
        r'|[\U0001F680-\U0001F6FF]'  # transport & map symbols
        r'|[\U0001F700-\U0001F77F]'  # alchemical symbols
        r'|[\U0001F780-\U0001F7FF]'  # Geometric Shapes Extended
        r'|[\U0001F800-\U0001F8FF]'  # Supplemental Arrows-C
        r'|[\U0001F900-\U0001F9FF]'  # Supplemental Symbols and Pictographs
        r'|[\U0001FA00-\U0001FA6F]'  # Chess Symbols
        r'|[\U0001FA70-\U0001FAFF]'  # Symbols and Pictographs Extended-A
        r'|[\U00002700-\U000027BF]'  # Dingbats
        r'|[\U0001F1E0-\U0001F1FF]'  # flags (iOS)
    )

    # Find all emojis
    emojis = re.findall(emoji_pattern, text)

    # Split text on emojis, keep them as part of the split
    split_text = re.split(f'({emoji_pattern.pattern})', text)

    emoji_list = []
    for i in range(1, len(split_text), 2):  # Iterating over emojis
        emoji = split_text[i]
        preceding_text = split_text[i - 1].strip()  # Get the text before the emoji
        
        # Count the number of words preceding the emoji
        word_count = len(preceding_text.split())
        
        # Duplicate the emoji based on the word count
        emoji_list.extend([emoji] * word_count)

    return emoji_list

if __name__ == "__main__":
    # Example input
    input_text = "Oh my god I am literally obsessed with Cristiano Ronaldo He is like the best soccer player ever and the song comma to 00 is like Sioux Fire matches his skills perfectly"
   
    # Extract timestamps from SRT file
    with open("temp//temp.srt", "r") as f:
        data = f.read()
        emoji_timestamps = extract_timestamps(data)
    
    session_groq = Groq(api_key = "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")

    # Extract emoji list
    emoji_list = emojifier(session_groq, input_text)
    print(emoji_list)
    
    # Make emoji clips
    emoji_clips = create_emoji_clips(emoji_list, emoji_timestamps)
