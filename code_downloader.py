from util_downloader.tiktok_downloader import download_tiktoks

import requests
import asyncio
import shutil
import json
import os


# Running main
if __name__ == '__main__':

    shutil.rmtree('./input')
    os.mkdir('./input')

    test = True
    clip_count = 5

    token_telegram = '7522802195:AAGZQptOGdKDAkiY79t_nX8lfBViOFSLdlI'
    url = f"https://api.telegram.org/bot{token_telegram}"

    # Reading the config file with users and their interests
    if test: 
        with open('config_test.json', 'r') as f: config = json.load(f)
    else: 
        with open('config.json', 'r') as f: config = json.load(f)

    for id in config["users"]:
        for topic in config["users"][id]['topics']:

            print(f"Sending raw {topic.upper()} topic videos for {id}...")
            response = requests.post(url + "/sendMessage", data={'chat_id': id, 'protect_content': 'false', 'text': f"Sending raw {topic.upper()} videos."})

            asyncio.run(download_tiktoks(clip_count, topic))

    metadata = json.load(open("input//json_metadata.json"))

    for file in os.listdir("input"):
        if file.endswith(".mp4"):
            for video in metadata:
                if video['id'] in file:
                    for id in config["users"]:
                        for topic in config["users"][id]['topics']:
                            with open("input//"+file, 'rb') as video_file: requests.post(url + "/sendVideo", files={'video': video_file}, data={'chat_id': id, 'protect_content': 'false', 'caption': video['id']})