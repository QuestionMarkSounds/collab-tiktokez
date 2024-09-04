import asyncio
import os
from TikTokApi import TikTokApi
import requests

ms_token = os.environ.get(
    "ms_token", None
) 
context_options = {
    'viewport' : { 'width': 1280, 'height': 1024 },
    'user_agent' : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36'
}

async def trending_videos():
    async with TikTokApi() as api:
        await api.create_sessions(ms_tokens=[ms_token], num_sessions=1, sleep_after=3, context_options=context_options)
        async for video in api.hashtag(name="trump").videos(count=5):
            info = video.as_dict
            print("-------------------------------")
            bitrate = info['video']['bitrate']
            for i in info['video']['bitrateInfo']:
                if bitrate == i["Bitrate"]:
                    response = requests.get(i["PlayAddr"]["UrlList"][-1])
                    if response.status_code == 200:
                        with open("tt_vids/{}.mp4".format(video.id), "wb") as f:
                            f.write(response.content)

if __name__ == "__main__":
    asyncio.run(trending_videos())