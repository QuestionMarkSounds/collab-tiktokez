import asyncio
import os
from TikTokApi import TikTokApi
import requests
import random
import json
import pyktok as pyk

context_options = {'viewport' : { 'width': 1280, 'height': 1024 }, 'user_agent' : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36'}

with open('json_metadata.json', 'r') as f: json_metadata = json.load(f)

async def download_tiktoks(count, topic):
    async with TikTokApi() as api:
        await api.create_sessions(num_sessions=1, sleep_after=3, context_options=context_options)

        counter = 0
        # async for video in api.hashtag(name=f"{topic}").videos():
        async for video in api.hashtag(name=f"{topic}").videos(count=30, cursor=random.randint(0, 150)):
            video_dict = video.as_dict

            if video_dict.get('video').get('duration') <= 20: continue
            if video_dict.get('video').get('duration') > 60: continue
        
            json_metadata[f"{topic}_{counter+1}"] = {
                "description_extracted": video_dict.get('desc'),
                "description_manual": ""
            }
            
            pyk.save_tiktok(f"https://www.tiktok.com/@{video_dict.get('author').get('uniqueId')}/video/{video_dict.get('video').get('id')}?is_copy_url=1&is_from_webapp=v1",
	        True,'video_data.csv','chrome')

            for file in os.listdir('.'):
                if file.endswith(".mp4"): os.rename(file, f"input/{topic}_{counter+1}.mp4")

            counter += 1
            if counter >= count: break

        with open('json_metadata.json', 'w') as file:
            json.dump(json_metadata, file, indent=2)

if __name__ == "__main__":
    asyncio.run(download_tiktoks(5, "supercar"))