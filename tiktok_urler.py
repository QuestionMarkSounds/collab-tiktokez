from TikTokApi import TikTokApi
import asyncio
import os
import requests
from dotenv import load_dotenv

load_dotenv()

ms_token = os.getenv("MS_TOKEN")

async def trending_videos():
    async with TikTokApi() as api:
        await api.create_sessions(ms_tokens=[ms_token], num_sessions=1, sleep_after=3)
        async for video in api.hashtag(name="donaldtrump").videos(count=30):
            info = video.as_dict
            print("-------------------------------")
            bitrate = info['video']['bitrate']
            for i in info['video']['bitrateInfo']:
                if bitrate == i["Bitrate"]:
                    response = requests.get(i["PlayAddr"]["UrlList"][-1])
                    if response.status_code == 200:
                        with open("tt_vids/{}.mp4".format(video.id), "wb") as f:
                            f.write(response.content)
                        # print("Video downloaded successfully!")
                
            # print(info['video']['bitrateInfo'][0]['qualityLabel'])
if __name__ == "__main__":
    asyncio.run(trending_videos())