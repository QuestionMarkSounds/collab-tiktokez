from simple_youtube_api.Channel import Channel
from simple_youtube_api.LocalVideo import LocalVideo
import time
import json
import os


with open(f"json_config.json", 'w') as file: json_config = json.load(file)

for channel in os.listdir('output'):
    with open(f"./output/{channel}/json_metadata.json", 'w') as file: json_metadata = json.load(file)

    account = json_config[channel]['account']

    session_channel = Channel()
    session_channel.login(f"data/accounts/{account}/client_secret.json", f"data/accounts/{account}/channels/{channel}/credentials.storage")

    # setting up the video that is going to be uploaded
    video = LocalVideo(file_path=f"output/{channel}/clip.mp4")

    # setting snippet
    video.set_title(json_metadata['title'])
    video.set_description(json_metadata['description'])
    # video.set_tags(["Amazing", "Beautiful", "Nature"])
    video.set_default_language("en-US")

    # setting status
    video.set_embeddable(True)
    video.set_license("creativeCommon")
    video.set_privacy_status("public")
    video.set_public_stats_viewable(False)

    # setting thumbnail
    # video.set_thumbnail_path('test_thumb.png')

    # uploading video and printing the results
    video = channel.upload_video(video)
    print(video.id)
    # print(video)

    time.sleep(10)