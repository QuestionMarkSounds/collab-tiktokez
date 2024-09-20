from simple_youtube_api.Channel import Channel
from simple_youtube_api.LocalVideo import LocalVideo

account = "helperchars@gmail.com"
channel_name = "travel"
video = "travel_1"

# loggin into the channel
channel = Channel()
channel.login(f"data/accounts/{account}/client_secret.json", f"data/accounts/{account}/channels/{channel_name}/credentials.storage")

# setting up the video that is going to be uploaded
video = LocalVideo(file_path=f"output/{video}.mp4")

# setting snippet
video.set_title("Exploring the Wild Beauty of Tanzania")
video.set_description("#Travel #Africa #Tourism")
video.set_tags(["Amazing", "Beautiful", "Nature"])
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