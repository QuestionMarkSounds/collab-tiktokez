Downloader:

Reads a config file in which the users indicate their topics of interest

Downloads 5 videos per topic to the output folder, and saves the metadata for those videos within the metadata json
Sends videos to the users based on the metadata, reading users topics and matching sent videos by topic



Processor:

Reads the list of selected videos for processing
For each video:
    Reads description in metadata, generates intro, title, description, outro
    Adds intro and outro
    Sends the video with title and description