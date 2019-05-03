#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# download_bot.py - Bot written in Python that, when given a URL to a file
#   through its message queue, downloads it into a globally specified directory
#   for storage.
#
#   This is part of the Exocortex Halo project
#   (https://github.com/virtadpt/exocortex-halo/).

# By: The Doctor <drwho at virtadpt dot net>
#       0x807B17C1 / 7960 1CDC 85C9 0B63 8D9F  DD89 3BD8 FF2B 807B 17C1

# License: GPLv3

# v2.1 - Added user-definable text to the help and about-to-do-stuff parts.
#       - Changed the default polling time to 10 seconds, because this bot
#        won't be run on a Commodore 64...
#       - Broke the online help out into a separate function.
# v2.0 - Ported to Python 3.
# v1.2 - Added "download this as an MP3" support.
# v1.1 - Added youtube-dl support.
# v1.0 - Initial release.

# TO-DO:
# - Write a better command parser, because this is getting bad.

# Load modules.
import argparse
import configparser
import json
import logging
import os
import os.path
import re
import requests
import sys
import time

# Global variables.
# Handle to a logging object.
logger = None

# Path to and name of the configuration file.
config_file = ""

# Loglevel for the bot.
loglevel = logging.INFO

# The "http://system:port/" part of the message queue URL.
server = ""

# URL to the message queue to take marching orders from.
message_queue = ""

# The name the search bot will respond to.  The idea is, this bot can be
# instantiated any number of times with different config files to use
# different search engines on different networks.
bot_name = ""

# How often to poll the message queues for orders.
polling_time = 10

# Directory to download files into.
download_directory = ""

# Handle to an download request from the user.
download_request = None

# Flag that determines if youtube-dl is available as a module.
video_enabled = False

# Flag that determines if ffmpeg is enabled, which will enable audio-only
# media downloads.
ffmpeg_enabled = False

# Flag that determines if a video stream will be downloaded.
download_video = False

# Flag that determines if an audio stream will be downloaded.
download_audio = False

# Optional user-defined text strings for the online help and user interaction.
user_text = None
user_acknowledged = None

# Functions.
# set_loglevel(): Turn a string into a numerical value which Python's logging
#   module can use because.
def set_loglevel(loglevel):
    if loglevel == "critical":
        return 50
    if loglevel == "error":
        return 40
    if loglevel == "warning":
        return 30
    if loglevel == "info":
        return 20
    if loglevel == "debug":
        return 10
    if loglevel == "notset":
        return 0

# parse_download_request(): Takes a string and figures out if it was a correctly
#   formatted request to download a file.  Requests are of the form "download
#   <some URL here>".  Returns the URL to download from or None if it's not a
#   well-formed request.
def parse_download_request(download_request):
    logger.debug("Entered function parse_download_request().")
    download_url = ""
    words = []

    # Make the download_[video,audio] flags available from the top level.
    global download_video
    global download_audio

    # Clean up the download request.
    download_request = download_request.strip()
    download_request = download_request.strip(",")
    download_request = download_request.strip(".")
    download_request = download_request.strip("'")

    # If the download request is empty (i.e., nothing in the queue) return None.
    if "no commands" in download_request:
        logger.debug("Got an empty download request.")
        return None

    # Tokenize the download request.
    words = download_request.split()
    logger.debug("Tokenized download request: " + str(words))

    # Start parsing the the download request to see what kind it is.  After
    # making the determination, remove the words we've sussed out to make the
    # rest of the command easier.

    # User asked for help.
    if not len(words):
        return None
    if words[0].lower() == "help":
        logger.debug("User asked for online help.")
        return words[0]

    # User asked the construct to download from a URL.
    if (words[0] == "download") or (words[0] == "get") or (words[0] == "pull"):
        logger.info("Got a token that suggests that this is a download request.")
    del words[0]

    # User asked the construct to download a media stream with youtube-dl.
    if (words[0] == "stream") or (words[0] == "video"):
        logger.info("Got a token that suggests that this is a media download request.")
        if video_enabled:
            download_video = True
            logger.info("Enabling media stream download.")
            del words[0]
        else:
            logger.error("User wants to download a media stream but that capability isn't enabled.")
            return None

    # User asked the construct to download an audio stream with youtube-dl.
    if (words[0] == "mp3") or (words[0] == "audio"):
        logger.info("Got a token that suggests that this is an audio download request.")
        if ffmpeg_enabled:
            download_video = True
            download_audio = True
            logger.info("Enabling audio stream download.")
            del words[0]
        else:
            logger.error("User wants to download an audio stream but that capability isn't enabled.")
            return None

    # If the parsed search term is now empty, return an error.
    if not len(words):
        logger.error("The download request appears to be empty.")
        return None

    # Convert the remainder of the list into a URI-encoded string.
    download_url = words[0]
    logger.debug("Download URL: " + download_url)
    return download_url

# download_file(): Function that takes as its arguments a directory to put
#   files into and a URL to download a file from.
def download_file(download_directory, url):
    logger.debug("Entered function download_file().")

    # Handle to an HTTP(S) request.
    request = None

    # Generic flag that determines whether or not the process worked.
    result = False

    # Local filename to write the file to.
    local_filename = url.split('/')[-1]

    # Full path to write the file to.
    full_path = os.path.join(download_directory, local_filename)
    full_path = os.path.normpath(full_path)
    logger.info("I will attempt to store the downloaded file as: " + str(full_path))

    # Download the file.
    try:
        request = requests.get(url, stream=True)
        with open(full_path, 'wb') as local_file:
            for chunk in request.iter_content(chunk_size=1024):
                if chunk:
                    local_file.write(chunk)
        result = True
        send_message_to_user("Successfully downloaded file: " + str(full_path))
    except:
        logger.warn("Unable to download from URL " + str(url) + " or write to file " + str(full_path))
        send_message_to_user("I was unable to download from URL " + str(url) + " or write to file " + str(full_path))

    # Return the result.
    return result

# mp3_download_hook(): Function that takes a youtube-dl status object as an
#   argument.  Doesn't return anything but does send the user a message.
# Keys possessed by status:
#   status, downloaded_bytes, filename, elapsed, total_bytes
def mp3_download_hook(status):
    if status["status"] == "finished":
        send_message_to_user("Done downloading media stream.  Now converting to MP3.")
    return

# download_media(): Function that takes as its arguments a directory to store
#   the downloaded media file into and a URL to download a stream from.
def download_media(download_directory, url):
    logger.debug("Entered function download_media().")

    # Make the "download a media stream" flags accessible.
    global download_video
    global download_audio

    # Generic flag that determines whether or not the process worked.
    result = False

    # Hash contianing options used by youtube_dl.
    options = {}

    # youtube-dl has an unusual way of specifying the destination
    # directory: It has to go in a template specifying what the filename
    # will look like when the download is complete.  I've hardcoded the
    # template here because it's basically the default anyway.
    options["outtmpl"] = download_directory + "/%(title)s-%(id)s.%(ext)s"
    options["outtmpl"] = os.path.normpath(options["outtmpl"])

    # If we're downloading an audio stream, set a few extra options.
    if download_audio:
        logger.debug("Handling an audio stream download request.")
        options["format"] = "bestaudio/best"
        options["postprocessors"] = [ {
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "128"
        } ]
        options["progress_hooks"] = [ mp3_download_hook ]
    logger.debug("Value of options{}: " + str(options))

    # The .download() method takes as its argument an array of strings.
    download = [ url ]

    # This is kinda clunky but it's in the official docs...
    try:
        with youtube_dl.YoutubeDL(options) as ydl:
            ydl.download(download)
        result = True
        send_message_to_user("Successfully downloaded media stream: " + str(url))
    except:
        send_message_to_user("Something went wrong - I wasn't able to download the media stream at " + str(url))

    # Reset the media flags because we don't want them to get stuck.
    download_video = False
    download_audio = False

    # Return the result.
    return result

# send_message_to_user(): Function that does the work of sending messages back
# to the user by way of the XMPP bridge.  Takes one argument, the message to
#   send to the user.  Returns a True or False which delineates whether or not
#   it worked.
def send_message_to_user(message):
    # Headers the XMPP bridge looks for for the message to be valid.
    headers = {"Content-type": "application/json"}

    # Set up a hash table of stuff that is used to build the HTTP request to
    # the XMPP bridge.
    reply = {}
    reply["name"] = bot_name
    reply["reply"] = message

    # Send an HTTP request to the XMPP bridge containing the message for the
    # user.
    request = requests.put(server + "replies", headers=headers,
        data=json.dumps(reply))

# online_help(): Utility function that sends online help to the user when
#   requested.  Takes no args.  Returns nothing.
def online_help():
    reply = "My name is " + bot_name + " and I am an instance of " + sys.argv[0] + ".\n\n"
    if user_text:
        reply = reply + user_text + "\n\n"
    reply = reply + "I am capable of accepting URLs for arbitrary files on the web and downloading them.  To download a file, send me a message that looks something like this:\n\n"
    reply = reply + bot_name + ", [download,get,pull] https://www.example.com/foo.pdf\n\n"
    reply = reply + "I will download files into: " + download_directory + "\n"
    send_message_to_user(reply)
    if video_enabled:
        reply = "I am youtube-dl enabled, and so can download any media stream this module is capable of.  To download a supported media, stream, send me a message that looks like this:\n\n"
        reply = reply + bot_name + ", [download,get] [stream,video] https://youtube.com/foo\n"
        send_message_to_user(reply)
    if ffmpeg_enabled:
        reply = "I am also capable of downloading and saving just the audio portion of video streams and saving them as MP3 files.  To download an MP3 from a stream, send me a message that looks like this:\n"
        reply = reply + bot_name + ", [download,get] [audio,mp3] https://youtube.com/foo\n"
        send_message_to_user(reply)
    return

# Core code...
# Set up the command line argument parser.
argparser = argparse.ArgumentParser(description="A bot that polls a message queue for URLs to files to download and downloads them into a local directory.")

# Set the default config file and the option to set a new one.
argparser.add_argument("--config", action="store",
    default="./download_bot.conf")

# Loglevels: critical, error, warning, info, debug, notset.
argparser.add_argument("--loglevel", action="store",
    help="Valid log levels: critical, error, warning, info, debug, notset.  Defaults to info.")

# Time (in seconds) between polling the message queues.
argparser.add_argument("--polling", action="store", help="Default: 10 seconds")

# Parse the command line arguments.
args = argparser.parse_args()
if args.config:
    config_file = args.config

# Read the options in the configuration file before processing overrides on the
# command line.
config = configparser.ConfigParser()
if not os.path.exists(config_file):
    logging.error("Unable to find or open configuration file " +
        config_file + ".")
    sys.exit(1)
config.read(config_file)

# Get the URL of the message queue to contact.
server = config.get("DEFAULT", "queue")

# Get the names of the message queues to report to.
bot_name = config.get("DEFAULT", "bot_name")

# Construct the full message queue URL.
message_queue = server + bot_name

# Get the default loglevel of the bot.
config_log = config.get("DEFAULT", "loglevel").lower()
if config_log:
    loglevel = set_loglevel(config_log)

# Set the number of seconds to wait in between polling runs on the message
# queues.
try:
    polling_time = config.get("DEFAULT", "polling_time")
except:
    # Nothing to do here, it's an optional configuration setting.
    pass

# Get the path to the ffmpeg executable.  If it's present, AND if youtube-dl
# support is present, the bot will be able to download and store audio tracks
# from video streams upon request.
ffmpeg_enabled = config.get("DEFAULT", "ffmpeg")

# Get the directory to store files in.
download_directory = config.get("DEFAULT", "download_directory")

# Normalize the download directory.
download_directory = os.path.abspath(os.path.expanduser(download_directory))

# Ensure the download directory exists.
if not os.path.exists(download_directory):
    print("ERROR: Download directory " + download_directory + " does not exist.")
    sys.exit(1)

# Ensure that the bot can write to the download directory.
if not os.access(download_directory, os.R_OK):
    print("ERROR: Unable to read contents of directory " + download_directory)
    sys.exit(1)
if not os.access(download_directory, os.W_OK):
    print("ERROR: Unable to write to directory " + download_directory)
    sys.exit(1)

# Get user-defined doing-stuff text if defined in the config file.
try:
    user_text = config.get("DEFAULT", "user_text")
except:
    # Nothing to do here, it's an optional configuration setting.
    pass

# Get additional user text if defined in the config file.
try:
    user_acknowledged = config.get("DEFAULT", "user_acknowledged")
except:
    # Nothing to do here, it's an optional configuration setting.
    pass

# Set the loglevel from the override on the command line.
if args.loglevel:
    loglevel = set_loglevel(args.loglevel.lower())

# Configure the logger.
logging.basicConfig(level=loglevel, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Set the message queue polling time from override on the command line.
if args.polling:
    polling_time = args.polling

# Try to import youtube_dl if it's available.
try:
    import youtube_dl
    video_enabled = True
except:
    pass

# Debugging output, if required.
logger.info("Everything is set up.")
logger.debug("Values of configuration variables as of right now:")
logger.debug("Configuration file: " + config_file)
logger.debug("Server to report to: " + server)
logger.debug("Message queue to report to: " + message_queue)
logger.debug("Bot name to respond to search requests with: " + bot_name)
logger.debug("Time in seconds for polling the message queue: " +
    str(polling_time))
logger.debug("Download directory: " + download_directory)
if video_enabled:
    logger.debug("This instance of download_bot.py is youtube-dl enabled.")
if ffmpeg_enabled:
    logger.debug("This instance of download_bot.py can save MP3s.")
if user_text:
    logger.debug("User-defined help text: " + user_text)
if user_acknowledged:
    logger.debug("User-defined command acknowledgenent text: " + user_acknowledged)

# Go into a loop in which the bot polls the configured message queue with each
# of its configured names to see if it has any download requests waiting for it.
logger.debug("Entering main loop to handle requests.")
send_message_to_user(bot_name + " now online.")
while True:
    download_request = None

    # Check the message queue for download requests.
    try:
        logger.debug("Contacting message queue: " + message_queue)
        request = requests.get(message_queue)
    except:
        logger.warn("Connection attempt to message queue timed out or failed.  Going back to sleep to try again later.")
        time.sleep(float(polling_time))
        continue

    # Test the HTTP response code.
    # Success.
    if request.status_code == 200:
        logger.debug("Message queue " + bot_name + " found.")

        # Extract the download request.
        download_request = json.loads(request.text)
        logger.debug("Value of download_request: " + str(download_request))
        download_request = download_request['command']

        # Parse the download request.
        download_request = parse_download_request(download_request)

        # If the index request comes back None (i.e., it wasn't well formed)
        # throw an error and bounce to the top of the loop.
        if not download_request:
            time.sleep(float(polling_time))
            continue

        # If the user is requesting help, assemble a response and send it back
        # to the server's message queue.
        if download_request.lower() == "help":
            online_help()
            continue

        # Handle the download request.
        if download_video:
            reply = "Downloading media stream."
            send_message_to_user(reply)
            download_request = download_media(download_directory,
                download_request)
        else:
            if user_acknowledged:
                send_message_to_user(user_acknowledged)
            else:
                reply = "Downloading file now.  Please stand by."
                send_message_to_user(reply)
            download_request = download_file(download_directory,
                download_request)

        # If something went wrong... the notice is sent earlier, so just
        # continue at the top of the loop.
        if not download_request:
            continue

    # Message queue not found.
    if request.status_code == 404:
        logger.info("Message queue " + bot_name + " does not exist.")

    # Sleep for the configured amount of time.
    time.sleep(float(polling_time))

# Fin.
sys.exit(0)
