import asyncio
import os
from TikTokApi import TikTokApi
import requests
import json

ms_token = os.environ.get("ms_token", None) 
context_options = {'viewport' : { 'width': 1280, 'height': 1024 }, 'user_agent' : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36'}

with open('json_metadata.json', 'r') as f: json_metadata = json.load(f)

async def download_tiktoks(count, topic):
    async with TikTokApi() as api:
        await api.create_sessions(ms_tokens=[ms_token], num_sessions=1, sleep_after=3, context_options=context_options)

        counter = 0
        async for video in api.hashtag(name=f"{topic}").videos():
            video_dict = video.as_dict

            if video_dict.get('video').get('duration') <= 20: continue
            if video_dict.get('video').get('duration') > 60: continue

            json_metadata[f"{topic}_{counter+1}"] = video_dict.get('desc')

            bitrate = video_dict['video']['bitrate']
            for i in video_dict['video']['bitrateInfo']:
                if bitrate == i["Bitrate"]:
                    response = requests.get(i["PlayAddr"]["UrlList"][-1])
                    if response.status_code == 200:
                        with open("input/{}.mp4".format(f"{topic}_{counter+1}"), "wb") as f:
                            f.write(response.content)

            counter += 1
            if counter >= count: break

        with open('json_metadata.json', 'w') as file:
            json.dump(json_metadata, file, indent=2)

if __name__ == "__main__":
    asyncio.run(download_tiktoks(5, "Trump"))