from __future__ import unicode_literals
from youtube_dl import YoutubeDL 
from pytube import Channel, Playlist
from os.path import exists
from threading import Thread 
from time import ctime

from tkinter import *
from tkinter import ttk
from tkinter import filedialog, messagebox

from json import load, dump

# Variables used to save the location of selected file, for more convenient searching
file_path = '' # directory + file name
file_dir = '/' # directory only

# Types of series, could be a channel, playlist, or neither (unrecognized)
C = "Channel"
P = "Playlist"
U = "Unknown"

# to be used to know the what is being downloaded
VID = 'video'
SUB = 'subtitle'

# File to save what's been downloaded
PROGRESS_FILE = 'download_progress.json'

def get_file_name(): 
    global file_path, file_dir
    # Get the file's location
    file_path = filedialog.askopenfilename(initialdir=file_dir, title = "Select A File", filetypes=(("text files","*.txt"), ))
    # Get the file's name
    file_name = file_path.split('/')[-1]
    # Save the file's directory, for more convenient browsing when looking for another file
    file_dir = file_path[:-(len(file_name))]
    selected_file.set(file_name)

# Save the download progress to the file
def set_dl_progress(dl_progress):
    with open(PROGRESS_FILE, 'w') as file:
        dump(dl_progress, file) # saved as json
    return dl_progress

# Open the download progress file
def get_dl_progress():
    if exists(PROGRESS_FILE):
        with open (PROGRESS_FILE, 'r') as file:
            dl_progress = load(file) # open json object (which makes a python dict)
    else: # If the file doesn't exist, start progress from scratch
        status_update("Progress file not found. Making a new one...")
        dl_progress = set_dl_progress({}) 
    return dl_progress

def get_series_and_type(link):
    # Check to see if the link can be opened as a Channel
    try: c = Channel(link)
    except: pass
    else: 
        # If the link is a channel, return the Channel and type, C
        return (c, C)
    try: p = Playlist(link) # Even if not a link, doesn't cause an error. So need to check another way
    except: pass
    else:
        try: p.title # If this works, it's a playlist, if not it causes an error
        except: # If not a playlist (and not a channel), it's unrecognized
            status_update(f"{U}: {link} (Could be an internet error)") # Update the user about malformed link
            return (None, U) # return nothing and type, U
        else: return (p, P) # If no error was caused, it's a playlisy
        # I figured out what throws an error from testing Playlist and Channel in idle

def get_series_count(series):
    # get the number of series that are either channel or playlist
    c_count = 0
    p_count = 0
    for s in series:
        is_downloading = download_status.get()
        # if the user clicked 'stop', break this loop as well
        if not is_downloading:
            break
        # Count the types
        if s[1] == C: c_count = c_count + 1
        elif s[1] == P: p_count = p_count + 1
    return (c_count, p_count) # return the total of each

def get_series():
    global file_path
    status_update("Retrieving channels/playlists...")
    # Opens the file as links
    with open(file_path, 'r') as links:
        # takes every line in the file to be a link
        link_list = [link.strip() for link in links.readlines()]
        # Uses the previous function to determine the type of the links, and also get their respective Objects (either pytube.Channel or pytube.Playlist)
        series = [get_series_and_type(link) for link in link_list] 
        return series

def handle_download_error(video, e, content):
    is_downloading = download_status.get()
    # if the user clicked 'stop', don't bother retrying the download
    if not is_downloading:
        return
    # ask the user if he wants to retry
    retry = messagebox.askyesno(title="Retry?", message=f"Error: {e}\n\n{video.title} {content} failed to download. Retry?")
    if retry:
        status_update(f"Retrying...")
        # if retrying, call either the video or subtitle downloader 
        if content == VID: download_video(video, skip_subtitle=True)
        elif content == SUB: download_subtitle(video)
    else: status_update("Skipping...")

def download_subtitle(video):
    ydl_opts = {
        'writesubtitles': True, #Adds a subtitles file if it exists
        'writeautomaticsub': False, #Adds auto-generated subtitles file
        'subtitle': '--write-sub', #writes subtitles file in english
        'subtitlesformat':'srt', #writes the subtitles file in "srt" or "ass/srt/best"
        'skip_download': True, #skips downloading the video file
        'subtitleslangs': ['ar'] #only arabic subtitles
        }
    with YoutubeDL(ydl_opts) as ydl:
        url = video.watch_url
        try: 
            ydl.download([url]) # downloads subtitle
        except Exception as e: # potentially a video error
            handle_download_error(video, e, content=SUB)

def download_video(video, skip_subtitle=False):
    if not skip_subtitle:
        download_subtitle(video)
    try:
        video.streams.get_by_itag(22).download(timeout=1000) # downloads video
    except Exception as e: # if an error occurs (renamed error to 'e')
        handle_download_error(video, e, content=VID) # send the video and error
    else: # if the download worked...
        status_update("Video downloaded.") # if download worked
        

def download_videos(series, s_type):
    dl_progress = get_dl_progress()

    # if the series is a playlist, get the playlist_id; if it's a channel, get the channel_id
    if s_type == P: series_id = series.playlist_id
    elif s_type == C: series_id = series.channel_id

    if series_id in dl_progress: 
        # if the series has already been checked (1 video downloaded), ask the user if they want to continue
        continue_progress = messagebox.askyesno(title="Proceed?", message="Continue download where you left off?")
        if continue_progress:
            series_progress = dl_progress[series_id] # if continue, get old progress
        else: series_progress = 0 # else, start progress at 0
    else:
        # if new series, start progress for it from 0
        dl_progress[series_id] = 0
        series_progress = 0

    # Get videos from the channel/playlist and their count
    videos = series.videos 
    video_count = len(videos)

    # Update message
    if series_progress > 0:
        status_update(f"Videos checked: {series_progress}/{video_count}.")
    else:
        status_update(f"Checking all videos... ({video_count})")

    increment = 100.0 / video_count # calculate increment for progress bar
    current_progress = series_progress * increment # start point for progress bar
    progress_update(current_progress) # updates the progress bar

    for video in reversed(videos)[series_progress:]: # reversed so it goes old->new; in case new videos are uploadedm they get downloaded in this way
        is_downloading = download_status.get()
        # if the user clicked 'stop', break the download loop
        if not is_downloading:
            break
        if 'ar' in video.captions:
            status_update(f"Found: {video.title}.")
            download_video(video, skip_subtitle=False) # download video with Arabic subtitles
        series_progress = series_progress + 1
        dl_progress[series_id] = series_progress
        set_dl_progress(dl_progress)
        progress_update(increment, increment=True) # update progress bar

def download_setup():
    progress_update(0.0) # reset progress bar
    series = get_series()

    # Count and display the total amount of channels and playlists, each
    c_count, p_count = get_series_count(series) 
    series_counter.set(f" {c_count}C and {p_count}P found")
    
    for s in series: # work on downloading channel videos
        is_downloading = download_status.get()
        # if the user clicked 'stop', this process gets stopped as well
        if not is_downloading:
            break
        s_type = s[1]
        # Tell user which series is getting checked, based on whether its a playlist or channel and its relevant attributes
        if s_type == P:
            status_update(f"Checking {P}: '{s[0].title}' ({s[0].playlist_id})")
            download_videos(s[0], s_type)
        elif s_type == C:    
            status_update(f"Checking {C}: '{s[0].channel_name}' ({s[0].channel_id})")
            download_videos(s[0], s_type)
    
    status_update("Done.")
    is_downloading = download_status.get()
    if is_downloading:
        change_download_status()

def handle_download():
    is_downloading = download_status.get()
    # if there isn't a download going on, begin downloading
    if not is_downloading:
        change_download_status() # go into a downloading state
        Thread(target=download_setup).start() # Start a different thread for processing
        # If the downloading took place in the same thread, the gui would freeze as the thread is occupied with the download and can't refresh
    else: # if there is a download currently, stop it and change the state
        status_update("Stopping progress (once current process is finished).")
        change_download_status()

def change_download_status():
    is_downloading = download_status.get() # get the download status
    # reverse the download status, and change the 'download' button's text appropriately
    if is_downloading:
        download_status.set(False)
        download_prompt.set("Download")
    else:  
        download_status.set(True)
        download_prompt.set("Stop")

def progress_update(num, increment=False):
    if increment:
        num = progress_point.get() + num
        increment = False
    # updates the real progress and the formatted progress to be shown on screen
    progress_point.set(num)
    progress_percent.set(f"{num:3.1f}%") # Formats the number so the digits before the decimal point take 3 spaces, and only one decimal number is shown

def status_update(text):
    # Updates the text box
    text = f"{text} | {ctime()}"
    status_text['state'] = 'normal' # unlocks the text-box for updates
    status_text.insert('end', f"{text}\n") # appends the update
    status_text.see('end') # focussed on the last entry in the text box
    status_text['state'] = 'disabled' # locks the text-box to avoid editting
    root.update() # refreshed the whole window, since Text requires refreshing, unlike when using StringVar

root = Tk() # Make window
root.title("Youtube Downloader") # Set title of window
root.resizable(False, False) # disables resizing of window, since it doesn't help (at least on windows)

frame = ttk.Frame(root, padding='10') # Make frame to house all widgets
frame.grid(column=0, row=0, sticky=(N, W, E, S)) # Show frame

ttk.Button(frame, text="Select a file", command=get_file_name, width=20).grid(column=0, row=0, sticky=(N, S)) # Button to select the file

selected_file = StringVar() # Variable to the show selected file
ttk.Label(frame, textvariable=selected_file, width=20, justify='center',background='white').grid(column=1, row=0, sticky=(E, W, N, S)) # Label that displays the selected file

series_counter = StringVar() # Variable to show number of series (channels and playlists)
ttk.Label(frame, textvariable=series_counter, justify='right', width=15).grid(column=2, row=0, sticky=(N, S, E, W)) # A label to display the series count for a file

download_status = BooleanVar(value=False) # True if downloading, false otherwise
download_prompt = StringVar(value="Download") # Variable to display 'download' if there isn't a download going on, and 'stop' otherwise
ttk.Button(frame, textvariable=download_prompt, command=handle_download, width=20).grid(column=0, row=1, sticky=(N, S)) # Button to download/stop download

style = ttk.Style(root) # This style affects the whole window
style.theme_use('default') # Change it to a 'default' theme, which has a wide progress bar
progress_point = DoubleVar() # Progress bar variable
progress = ttk.Progressbar(frame, orient=HORIZONTAL, length=100, mode='determinate', maximum=100.0, variable=progress_point) # Progress bar settings, not displayed yet since it lacks .grid()
progress.grid(column=1, row=1, sticky=(E, W, N, S)) # show progress bar

progress_percent = StringVar() # Variable to display percent of download reached, for a single series
percent = ttk.Label(frame, textvariable=progress_percent, width=10)
percent.grid(column=2, row=1) # Label to display that percent

status_frame = ttk.Frame(frame, padding='5') # Frame to house status info
status_frame.grid(column=0, columnspan=3, row=2, sticky=(N, S, W, E)) # Display status info's frame

status_text = Text(status_frame, width=50, height = 7, wrap='none', state='disabled') # Status info text box settings
status_text.grid(column=0, row=0, sticky=(N, S, W, E)) # Displays the status info

status_scroll_y = ttk.Scrollbar(status_frame, orient=VERTICAL, command=status_text.yview) # Vertical scrollbar settings
status_scroll_x = ttk.Scrollbar(status_frame, orient=HORIZONTAL, command=status_text.xview) # Horizontal scrollbar settings
status_text.configure(yscrollcommand=status_scroll_y.set, xscrollcommand=status_scroll_x.set) # Configures the text box to recognize the scrollbars
# Display the scrollbars
status_scroll_y.grid(column=1, row=0, sticky=(N, S, W, E))
status_scroll_x.grid(column=0, row=1, sticky=(N, S, W, E))

root.mainloop() # Runs the GUI