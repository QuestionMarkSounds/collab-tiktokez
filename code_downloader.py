import requests
import asyncio
import shutil
import json
import os


# Running main
if __name__ == '__main__':

    shutil.rmtree('./input')
    os.mkdir('./input')
    with open('json_metadata.json', 'w') as file: json.dump({}, file)
    from util_tiktok_downloader.tiktok_downloader import download_tiktoks

    test = True
    clip_count = 5

    token_telegram = '7522802195:AAGZQptOGdKDAkiY79t_nX8lfBViOFSLdlI'
    url = f"https://api.telegram.org/bot{token_telegram}"

    # Reading the config file with users and their interests
    if test: 
        with open('json_config_test.json', 'r') as f: json_config = json.load(f)
    else: 
        with open('json_config.json', 'r') as f: json_config = json.load(f)

    for id in json_config["users"]:
        for topic in json_config["users"][id]['topics']:
            print(f"Downloading raw {topic.upper()} topic videos for {id}...")
            asyncio.run(download_tiktoks(clip_count, topic))

    json_metadata = json.load(open("json_metadata.json"))
    for user in json_config['users']:
        for topic in json_config['users'][user]['topics']:
            for file in os.listdir("input"):
                if file.endswith(".mp4"):
                    if file.split("_")[0] == topic:
                        with open("input//"+file, 'rb') as video_file: requests.post(url + "/sendVideo", files={'video': video_file}, data={'chat_id': id, 'protect_content': 'false', 'caption': f"{file.split(".")[0]}"})
