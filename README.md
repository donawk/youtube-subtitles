# youtube-subtitles
Python program to download YouTube videos (**with Arabic subtitles**) along with their subtitles.

GUI (implemented with Tkinter) allows user to choose a file containing a line-separated list of youtube channels and playlists to download from.

Videos must contain Arabic subtitles to be download, once chosen both the video and subtitles are saved locally.

## Setup
Install [Python](https://python.org) and run `pip install -r .\requirements.txt`

## Features

- Application fully implemented in GUI
- Saves download progress locally for each Channel/Playlist, to continue in case of unexpected errors (eg. internet, or youtube's API changing)
- Provides a download bar and an option to pause downloads
- Provides updates to user in GUI
- Moved on from command-bases text file selection to Tkinter's file dialog
- Heavily commented code, as per initial request