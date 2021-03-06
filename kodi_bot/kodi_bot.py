#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# kodi_bot.py - Bot written in Python that interfaces with a Kodi instance and
#   acts as a remote control for audio and video playback.
#
#   This is part of the Exocortex Halo project
#   (https://github.com/virtadpt/exocortex-halo/).

# By: The Doctor <drwho at virtadpt dot net>
#       0x807B17C1 / 7960 1CDC 85C9 0B63 8D9F  DD89 3BD8 FF2B 807B 17C1

# License: GPLv3

# v3.1 - Reworked the startup logic so that being unable to immediately
#       connect to either the message bus or the intended service is a
#       terminal state.  Instead, it loops and sleeps until it connects and
#       alerts the user appropriately.
#       - Changed logger.warn() to logger.warning().
# v3.0 - Ported to Python 3.
# v2.1 - Added ability to pause, unpause, and stop whatever's playing.  Added
#   corpora and helper methods to support this.
# v2.0 - Removed kodipydent, replaced it with direct HTTP calls to the Kodi
#   JSON RPC API using Requests.
# v1.0 - Initial release.

# TO-DO:
# - Figure out how to let the user add to and remove from the various corpora to
#   personalize the bots without having to shut down, edit the files manually,
#   and restart the bot.
# - Add to the command parser the ability to list the active command classes
#   and the corpora associated with them so the user has an idea of what to say.
# - Refactor the part of the do-stuff loop where the bot handles search
#   requests.  It's going to turn into a mess soon.  Maybe I should split it out
#   into a separate module...
# - Consider not running commands other than requests for help if the
#   confidence is too low.
# - Figure out how to detect the case where the media database for one Kodi
#   instance is being used with a different instance.
# - Add use of VideoLibrary.Scan and AudioLibrary.Scan to update Kodi's
#   internal database.  Then re-run the media library builder to update the
#   local copy.
# - Add the ability to ask the bot what's playing right now.

# Load modules.
import argparse
import configparser
import humanfriendly
import json
import logging
import os
import requests
import sys
import time

from requests.auth import HTTPBasicAuth

import help
import kodi_library
import parser

# Constants.
# When POSTing something to a service, the correct Content-Type value has to
# be set in the request.
headers = {
    "Content-Type": "application/json"
    }

# Global variables.
# Handle to a logging object.
logger = ""

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

# String that holds the command from the user prior to parsing.
user_command = ""

# String that holds the user's extracted search term.
search_term = ""

# Handle to a parsed user command.
parsed_command = None

# Kodi connection information.
kodi_host = ""
kodi_port = 0
kodi_user = ""
kodi_password = ""

# One or more media directories to search for media.
media_dirs = ""

# Directories to ignore.
exclude_dirs = []

# Directory containing text files to front-load the parser with.
corpora_dir = ""

# Minimum statistical confidence in a match.  Defaults to 25 out of 100.
minimum_confidence = 25

# Minimum statistical confidence in proper name matching.  Defaults to 80 out
# of 100.
match_confidence = 80

# Handle to a Requests object.
request = None

# Types of commands the bot can parse and act on.
commands_tmp = []
commands = {}

# List of media source directories on the Kodi box.
sources = {}

# Local copy of Kodi's media library because you can't actually search it, you
# can only download a copy and parse through it.
media_library = {}

# Number of points to increase or decrease the volume at a time.  Defaults to
# 10.
volume_step = 10

# Where to dump a local backup copy of the media library.
local_library = ""

# Handle to a search result.
search_result = None

# Handle to the thing you want to play.
media_to_play = None

# Hash of the enabled media playback subsystems on this Kodi instance.
enabled_players = {}

# Full URL to a Kodi instance.
kodi_url = ""

# Handle to an HTTP basic auth object.
kodi_auth = None

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

# send_message_to_user(): Function that does the work of sending messages back
# to the user by way of the XMPP bridge.  Takes one argument, the message to
#   send to the user.  Returns a True or False which delineates whether or not
#   it worked.
def send_message_to_user(message):
    # Set up a hash table of stuff that is used to build the HTTP request to
    # the XMPP bridge.
    reply = {}
    reply["name"] = bot_name
    reply["reply"] = message

    # Send an HTTP request to the XMPP bridge containing the message for the
    # user.
    request = requests.put(server + "replies", headers=headers,
        data=json.dumps(reply))

# kodi_settings(): A function that just returns the bot's configuration
#   settings.  Takes no arguments, references all of the global config
#   variables.  Returns a string.
def kodi_settings():
    reply = "These are my configuration settings:\n"
    reply = reply + "Message queue I report to: %s\n" % message_queue
    reply = reply + "Number of seconds in between polling for commands: %d\n" % polling_time
    reply = reply + "Kodi box that I control: %s:%d\n" % (kodi_host, kodi_port)
    reply = reply + "Media directories on the Kodi box that I look in for things to play: %s\n" % str(media_dirs)
    reply = reply + "Directories on the server I'm not checking for media: %s\n" % exclude_dirs
    reply = reply + "Minimum confidence in my understanding of your commands before I'll act on them: %d percent\n" % minimum_confidence
    reply = reply + "Minimum confidence in my searches of names, titles, and other proper names: %d percent\n" % match_confidence
    reply = reply + "Media sources I know about on the Kodi server: %s\n" % sources
    reply = reply + "When you tell me to change the volume, I change it by %d points each time.\n" % volume_step
    reply = reply + "I store local backup copies of the media library here: %s\n" % local_library
    reply = reply + "The size of your media library's database is %s, by the way.\n" % humanfriendly.format_size(os.path.getsize(local_library))
    return reply

# load_local_media_library(): Function that tries to load a local dump of the
#   Kodi media library if it exists.  Returns the loaded JSON dump if
#   successful, raise a generic Exception on failure.
def load_local_media_library(local_library):
    logger.debug("Entered load_local_media_library().")

    media_library = {}

    if os.path.exists(local_library):
        logger.info("Trying to load local copy of media library %s..." % local_library)
        with open(local_library, "r") as media_library_dump:
            try:
                media_library = json.load(media_library_dump)
            except:
                logger.warning("Unable to reload media library!  Building a new one from scratch!")
        return media_library
    else:
        raise Exception

# build_local_media_library(): Function that builds a local copy of the media
#   library by pulling the data out of Kodi.  Returns a hash table containing
#   all of the information.
def build_local_media_library():
    logging.debug("Entered build_local_media_library().")

    media_library = {}
    media_library = kodi_library.build_media_library(kodi_url, kodi_auth,
        headers, sources, exclude_dirs)

    # Load the media library from Kodi in steps, because there are multiple
    # library databases inside of Kodi.  This is simultaneously interesting,
    # opaque, and frustrating because I've been dorking around with this all
    # night.
    media_library["artists"] = kodi_library.get_artists(kodi_url, kodi_auth,
        headers)
    media_library["albums"] = kodi_library.get_albums(kodi_url, kodi_auth,
        headers)
    media_library["songs"] = kodi_library.get_songs(kodi_url, kodi_auth,
        headers)
    media_library["movies"] = kodi_library.get_movies(kodi_url, kodi_auth,
        headers)
    media_library["tv"] = kodi_library.get_tv_shows(kodi_url, kodi_auth,
        headers)

    # Load the genres Kodi knows about, which are kept separate from the rest
    # of the media metadata.
    media_library["audio_genres"] = kodi_library.get_audio_genres(kodi_url,
        kodi_auth, headers)
    media_library["video_genres"] = kodi_library.get_video_genres(kodi_url,
        kodi_auth, headers)

    return media_library

# get_enabled_players: Function that gets from Kodi a list of usable media
#   playback modules.  Takes three arguments, a Kodi URL, an HTTP Basic Auth
#   object, and a set of custom headers.  Returns a list of currently active
#   media players on the Kodi server.
def get_enabled_players(kodi_url, kodi_auth, headers):
    request = None
    enabled_players = None

    # Build a command to POST to Kodi.
    command = {}
    command["id"] = 1
    command["jsonrpc"] = "2.0"
    command["method"] = "Player.GetPlayers"

    request = requests.post(kodi_url, auth=kodi_auth, headers=headers,
        data=json.dumps(command))
    enabled_players = request.json()

    return enabled_players["result"]

# extract_search_term(): Takes two strings, a search term and a matching string
#   from a corpus.  Subtracts the latter from the former, hopefully leaving
#   just the user's actual search term (a name, a title, whatever).  Returns a
#   string.
def extract_search_term(search_term, matching_string):
    logging.debug("Entered kodi_bot.extract_search_term.")
    logging.debug("Search term: %s" % search_term)
    logging.debug("Matching string from the corpus: %s" % matching_string)

    result = None

    # Normalize and clean up the search term.
    search_term = search_term.lower()
    search_term = search_term.strip()
    search_term = search_term.strip("?")
    search_term = search_term.strip("!")
    search_term = search_term.strip(".")
    search_term = search_term.strip(":")
    search_term = search_term.strip(";")
    search_term = search_term.strip("'")
    search_term = search_term.split()

    # Normalize and clean up the matching string from the corpus.
    matching_string = matching_string.lower()
    matching_string = matching_string.strip()
    matching_string = matching_string.strip("?")
    matching_string = matching_string.strip("!")
    matching_string = matching_string.strip(".")
    matching_string = matching_string.strip(":")
    matching_string = matching_string.strip(";")
    matching_string = matching_string.strip("'")
    matching_string = matching_string.split()

    result = list(set(search_term) - set(matching_string))
    result = " ".join(result)
    logging.debug("Extracted search term: %s" % result)

    return result

# Core code... let's do this.
# Set up the command line argument parser.
argparser = argparse.ArgumentParser(description="A bot that interfaces with a Kodi media server.  It can run searches on the media library as well as send commands to the server.")

# Set the default config file and the option to set a new one.
argparser.add_argument("--config", action="store",
    default="./kodi_bot.conf")

# Loglevels: critical, error, warning, info, debug, notset.
argparser.add_argument("--loglevel", action="store",
    help="Valid log levels: critical, error, warning, info, debug, notset.  Defaults to info.")

# Time (in seconds) between polling the message queues.
argparser.add_argument("--polling", action="store", help="Default: 10 seconds")

# Whether or not to build a media library.  This exists to speed up debugging.
argparser.add_argument("--no-media-library", action="store_true",
    help="If this flag is set, the bot won't spend time generating a media library.  This speeds up debugging greatly.")

# Parse the command line arguments.
args = argparser.parse_args()
if args.config:
    config_file = args.config

# Read the options in the configuration file before processing overrides on the
# command line.
config = configparser.ConfigParser()
if not os.path.exists(config_file):
    logging.error("Unable to find or open configuration file %s." % config_file)
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
    polling_time = int(polling_time)
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

# Parse the rest of the configuration file...
# Get the Kodi configuration information.
kodi_host = config.get("DEFAULT", "kodi_host")
kodi_port = int(config.get("DEFAULT", "kodi_port"))
kodi_user = config.get("DEFAULT", "kodi_user")
kodi_password = config.get("DEFAULT", "kodi_password")
media_dirs = config.get("DEFAULT", "media_dirs")
media_dirs = media_dirs.split()
try:
    exclude_dirs = config.get("DEFAULT", "exclude_dirs").split(",")
except:
    # This is optional.
    pass

corpora_dir = config.get("DEFAULT", "corpora_dir")
minimum_confidence = int(config.get("DEFAULT", "minimum_confidence"))
match_confidence = int(config.get("DEFAULT", "match_confidence"))
commands_tmp = config.get("DEFAULT", "command_types").split(",")
volume_step = int(config.get("DEFAULT", "volume_step"))
try:
    local_library = config.get("DEFAULT", "local_library")
    local_library = os.path.abspath(local_library)
except:
    # This is optional.
    pass

# Build the Kodi URL.
kodi_url = "http://" + kodi_host + ":" + str(kodi_port) + "/jsonrpc"

# Debugging output, if required.
logger.info("Everything is set up.")
logger.debug("Values of configuration variables as of right now:")
logger.debug("Configuration file: %s" % config_file)
logger.debug("Server to report to: %s" % server)
logger.debug("Message queue to report to: %s" % message_queue)
logger.debug("Bot name to respond to search requests with: %s" % bot_name)
logger.debug("Time in seconds for polling the message queue: %d" % polling_time)
logger.debug("Kodi host: %s" % kodi_host)
logger.debug("Kodi port: %s" % kodi_port)
logger.debug("Kodi URL: %s" % kodi_url)
logger.debug("Kodi username: %s" % kodi_user)
logger.debug("Kodi password: %s" % kodi_password)
logger.debug("Media directories: %s" % str(media_dirs))
logger.debug("Directories to skip over: %s" % exclude_dirs)
logger.debug("Corpora to train the parser with: %s" % corpora_dir)
logger.debug("Minimum statistical match confidence: %d" % minimum_confidence)
logger.debug("Minimum statistical match confidence in proper names: %d" % match_confidence)
logger.debug("Volume change step size: %d" % volume_step)
if args.no_media_library:
    logger.debug("Not building a media library.")
if local_library:
    logger.debug("Location of local library dump: %s" % local_library)

# Try to contact the XMPP bridge.  Keep trying until you reach it or the
# system shuts down.
logger.info("Trying to contact XMPP message bridge...")
while True:
    try:
        send_message_to_user(bot_name + " now online.")
        break
    except:
        logger.warning("Unable to reach message bus.  Going to try again in %s seconds." % polling_time)
        time.sleep(float(polling_time))

# Build an HTTP basic auth object for Kodi and try to connect to a Kodi
# instance.
kodi_auth = HTTPBasicAuth(kodi_user, kodi_password)
while True:
    try:
        request = requests.get(kodi_url, auth=kodi_auth, headers=headers)
        send_message_to_user(bot_name + " connected to Kodi instance " + kodi_url + ".")
        break
    except:
        logger.error("Unable to connect to Kodi instance at %s with username %s and password %s.  Please check your configuration file." % (kodi_url, kodi_user, kodi_password))
        send_message_to_user("Unable to connect to Kodi instance at %s with username %s and password %s.  Please check your configuration file." % (kodi_url, kodi_user, kodi_password))
        time.sleep(float(polling_time))

# Load the corpora into a hash table where the keys are categories of commands
# to run and the values are empty lists.
for i in commands_tmp:
    commands[i] = []
commands = parser.load_corpora(corpora_dir, commands)
logger.debug("Command classes supported by the parser: %s" % str(list(commands.keys())))

# If the user asks that no media library be generated, skip this part.  It's
# nice, but it also gets in the way of debugging because it can take so long.
if args.no_media_library == False:
    # If a local copy of the media library exists, load it from disk.
    try:
        logger.info("Trying to load local media library...")
        media_library = load_local_media_library(local_library)
        logger.info("Success!")
    except:
        # Generate a list of media sources on the Kodi box.  From the Kodi docs,
        # there are only two we have to care about, video and music.  I'm using
        # the canonical Kodi names for consistency's sake.
        logger.info("No local media library loaded.  Generating a new one.")
        sources = kodi_library.get_media_sources(kodi_url, kodi_auth,
            headers)
        media_library = build_local_media_library()

        # Make a local backup of the media library to make startup faster.
        if local_library:
            logger.debug("Now making a local copy of media library for later.")
            with open(local_library, "w") as media_library_dump:
                json.dump(media_library, media_library_dump)
            logger.debug("Done.  File size is %s." % humanfriendly.format_size(os.path.getsize(local_library)))
else:
    logger.info("Skipping media library generation by request.")

# Get the media playback modules this Kodi server supports.
enabled_players = get_enabled_players(kodi_url, kodi_auth, headers)
if not enabled_players:
    logging.fatal("No media players reported by Kodi.  This is weird.")
    send_message_to_user("No media players reported by Kodi.  This is weird.  Terminating.")
    sys.exit(1)

# Go into a loop in which the bot polls the configured message queue with each
# of its configured names to see if it has any search requests waiting for it.
logger.debug("Entering main loop to handle requests.")
while True:
    user_command = None
    search_term = ""
    reply = ""

    # Check the message queue for index requests.
    try:
        logger.debug("Contacting message queue: %s" % message_queue)
        request = requests.get(message_queue)
    except:
        logger.warning("Connection attempt to message queue timed out or failed.  Going back to sleep to try again later.")
        time.sleep(float(polling_time))
        continue

    # Test the HTTP response code.
    # Success.
    if request.status_code == 200:
        logger.debug("Message queue %s found." % bot_name)

        # Extract the user command.
        user_command = json.loads(request.text)
        logger.debug("Value of user_command: %s" % user_command)
        user_command = user_command["command"]

        # Parse the user command.
        parsed_command = parser.parse(user_command, commands)
        logging.debug("Parsed command: %s" % parsed_command)

        # No command to parse.  Sleep, move on.
        if not parsed_command:
            time.sleep(float(polling_time))
            continue

        # If the bot's confidence interval on the match is below the minimum,
        # warn the user.
        if parsed_command["confidence"] <= minimum_confidence:
            logging.debug("Sending warning about insufficient confidence.")
            reply = "I think you should know that I'm not entirely confident I know what you mean.  I'm only about %d percent sure of my interpretation.  Were you asking about %s?" % (parsed_command["confidence"], parsed_command["match"])
            send_message_to_user(reply)

        # If the user is replying to the bot (they've been asked about
        # something specific), parse the reply and do something with it.
        #if media_to_play:
        #    media_to_play = None
        #    time.sleep(float(polling_time))
        #    continue

        # If the user is requesting help, get and return that help text to the
        # user.
        if parsed_command["match"] == "help_basic":
            logging.debug("Matched help_basic.")
            send_message_to_user(help.help_basic(bot_name, sys.argv[0]))
            continue
        if parsed_command["match"] == "help_commands":
            logging.debug("Matched help_commands.")
            send_message_to_user(help.help_commands())
            continue
        if parsed_command["match"] == "help_audio":
            logging.debug("Matched help_audio.")
            send_message_to_user(help.help_audio())
            continue
        if parsed_command["match"] == "help_video":
            logging.debug("Matched help_video.")
            send_message_to_user(help.help_video())
            continue

        # If the user is asking about the bot's settings, format them in a
        # message and send back to the user.
        if parsed_command["match"] == "kodi_settings":
            logging.debug("Matched kodi_settings.")
            send_message_to_user(kodi_settings())
            continue

        # If the user is asking to search the album subsection of the media
        # library, do the thing.
        if parsed_command["match"] == "search_requests_albums":
            logging.debug("Matched search_requests_albums.")
            reply = "I think you're asking me to search for an album title.  Just a moment, please..."
            send_message_to_user(reply)

            # Extract just the search term.
            search_term = extract_search_term(user_command,
                parsed_command["corpus"])

            # Run the search.
            search_result = kodi_library.search_media_library_albums(
                search_term, media_library["albums"], match_confidence)

            # Convert the array into a hash incorporating an array.
            search_result_tmp = {}
            search_result_tmp["type"] = "albums"
            search_result_tmp["search_results"] = search_result
            i = 1
            for j in search_result_tmp["search_results"]:
                j["entry"] = i
                i = i + 1
            search_result = search_result_tmp
            logging.debug("Value of search_result: %s" % str(search_result))

            # Figure out how confident we are in the search result's accuracy.
            for album in search_result["search_results"]:
                if not album["confidence"]:
                    reply = "I didn't find any matches."
                elif album["confidence"] == 100:
                    reply = "I found it!  %s is in your media library.  Would you like me to play it?" % album["label"]
                elif album["confidence"] >= minimum_confidence:
                    reply = "I think I found what you're looking for in your library: %s\nShall I play it?" % album["label"]
                else:
                    reply = "I'm not too sure about it, but I may have found something vaguely matching %s is in your media library.  I can play it if you like." % album["label"]

            # Store a reference to the media to play because later I want the
            # bot to be able to play what it found.
            media_to_play = search_result
            send_message_to_user(reply)
            continue

        # If the user is asking to search the media library for a particular
        # artist, do the thing.
        if parsed_command["match"] == "search_requests_artists":
            logging.debug("Matched search_requests_artists.")
            reply = "I think you're asking me to search for a particular artist or performer.  Just a moment, please..."
            send_message_to_user(reply)

            # Extract just the search term.
            search_term = extract_search_term(user_command,
                parsed_command["corpus"])

            # Run the search.
            search_result = kodi_library.search_media_library_artists(search_term,
                media_library["artists"], match_confidence)

            # Convert the array into a hash incorporating an array.
            search_result_tmp = {}
            search_result_tmp["type"] = "artists"
            search_result_tmp["search_results"] = search_result
            i = 1
            for j in search_result_tmp["search_results"]:
                j["entry"] = i
                i = i + 1
            search_result = search_result_tmp
            logging.debug("Value of search_result: %s" % str(search_result))

            # Figure out how confident we are in the search result's accuracy.
            for artist in search_result["search_results"]:
                if not artist["confidence"]:
                    reply = "I didn't find any matches."
                elif artist["confidence"] == 100:
                    reply = "I found it!  You have stuff by %s in your media library.  Would you like me to play it?" % artist["artist"]
                elif artist["confidence"] >= minimum_confidence:
                    reply = "I think I found who you're looking for: %s\nShall I play it?" % artist["artist"]
                else:
                    reply = "I'm not too sure, but I may have found someone vaguely matching %s in your media library.  Would you like me to play it?" % artist["artist"]

            # Store a reference to the media to play because later I want the
            # bot to be able to play what it found.
            media_to_play = search_result
            send_message_to_user(reply)
            continue

        # If the user is asking to search the media library for a particular
        # genre of music, do the thing.
        if parsed_command["match"] == "search_requests_genres":
            logging.debug("Matched search_requests_genres.")
            reply = "I think you're asking me to search for a particular genre of music.  Just a moment, please..."
            send_message_to_user(reply)

            # Extract just the search term.
            search_term = extract_search_term(user_command,
                parsed_command["corpus"])

            # Run the search.
            search_result = kodi_library.search_media_library_genres(search_term,
                media_library["audio_genres"], match_confidence)

            # Convert the array into a hash incorporating an array.
            search_result_tmp = {}
            search_result_tmp["type"] = "genres"
            search_result_tmp["search_results"] = search_result
            i = 1
            for j in search_result_tmp["search_results"]:
                j["entry"] = i
                i = i + 1
            search_result = search_result_tmp
            logging.debug("Value of search_result: %s" % str(search_result))

            # Build a reply to the user.
            if not len(search_result["search_results"]):
                reply = "It doesn't look like I found any matching genres in your media library.  You either don't have any, or your media's genre tags aren't amenable to searching and matching."
            if len(search_result["search_results"]) == 1:
                reply = "I found only one hit for that genre."
            if len(search_result["search_results"]) > 1:
                reply = "I found %d possible matching genres in your library.  I'm fairly sure that they're all minor variants of each other so I'm going to consider all of them valid." % len(search_result["search_results"])

            # Store a reference to the media to play because later I want the
            # bot to be able to play what it found.
            media_to_play = search_result
            send_message_to_user(reply)
            continue

        # If the user is asking to search the media library for a particular
        # song or track title, do the thing.
        if parsed_command["match"] == "search_requests_songs":
            logging.debug("Matched search_requests_songs.")
            reply = "I think you're asking me to search for a particular song or track title.  Just a moment, please..."
            send_message_to_user(reply)

            # Extract just the search term.
            search_term = extract_search_term(user_command,
                parsed_command["corpus"])

            # Run the search.  Start with the song library.
            search_result = kodi_library.search_media_library_songs(search_term,
                media_library["songs"], match_confidence)

            # Now check the music library.  Why this is a different thing, I
            # don't know.
            search_result = search_result + kodi_library.search_media_library_music(search_term,
                media_library["music"], match_confidence)

            # Deduplicate the search results because this might return identical
            # track titles.
            # After dorking around with this for too long, I went with this
            # solution.  Thanks, dnit13!
            # https://stackoverflow.com/questions/36486039/python-deduplicate-list-of-dictionaries-by-value-of-a-key
            delist = []
            tmplist = []
            for i in search_result:
                if i["label"] not in delist:
                    delist.append(i["label"])
                    tmplist.append(i)
            search_result = tmplist

            # Convert the array into a hash incorporating an array.
            search_result_tmp = {}
            search_result_tmp["type"] = "songs"
            search_result_tmp["search_results"] = search_result
            i = 1
            for j in search_result_tmp["search_results"]:
                j["entry"] = i
                i = i + 1
            search_result = search_result_tmp
            logging.debug("Value of search_result: %s" % str(search_result))

            # Build a reply to the user.
            if not len(search_result["search_results"]):
                reply = "It doesn't look like I found any matching tracks in your media library.  You might not have it, it may not have that title, or you mis-remembered the title somehow.  Or maybe your music metadata needs to be curated."
            if len(search_result["search_results"]) == 1:
                reply = "I found the song for you.  Do you want me to play it?"
            if len(search_result["search_results"]) > 1:
                reply = "I found %d possible matching tracks:\n\n" % len(search_result["search_results"])
                for i in search_result["search_results"]:
                    reply = reply + str(i["entry"]) + " - " + str(i["label"]) + "\n"
                reply = reply + "\nWhich one would you like me to play?"

            # Store a reference to the media to play because later I want the
            # bot to be able to play what it found.
            media_to_play = search_result
            send_message_to_user(reply)
            continue

        # If the user is asking to search the media library for a particular
        # video file, do the thing.
        if parsed_command["match"] == "search_requests_videos":
            logging.debug("Matched search_requests_videos.")
            reply = "I think you're asking me to search for a video file.  Just a moment, please..."
            send_message_to_user(reply)

            # Extract just the search term.
            search_term = extract_search_term(user_command,
                parsed_command["corpus"])

            # Run the search.
            search_result = kodi_library.search_media_library_video(search_term,
                media_library["video"], match_confidence)

            # Convert the array into a hash incorporating an array.
            search_result_tmp = {}
            search_result_tmp["type"] = "videos"
            search_result_tmp["search_results"] = search_result
            i = 1
            for j in search_result_tmp["search_results"]:
                j["entry"] = i
                i = i + 1
            search_result = search_result_tmp
            logging.debug("Value of search_result: %s" % str(search_result))

            # Build a reply to the user.
            if not len(search_result["search_results"]):
                reply = "It doesn't look like I found any matching filenames in your media library.  You either don't have it, or your filenames need cleaning up."
            if len(search_result["search_results"]) == 1:
                reply = "I found only one matching filename."
                media_to_play = search_result
            if len(search_result["search_results"]) > 1:
                reply = "I found %d possible matching filenames in your video library.\n\n" % len(search_result["search_results"])
                media_to_play = search_result
                for i in search_result["search_results"]:
                    reply = reply + str(i["entry"]) + " - " + str(i["label"]) + "\n"
                reply = reply + "\nWhich one would you like me to play?"

            # Store a reference to the media to play because later I want the
            # bot to be able to play what it found.
            send_message_to_user(reply)
            media_to_play = search_result
            continue

        # The user wants to pause what's currently playing.
        if parsed_command["match"] == "commands_pause":
            logging.debug("Matched commands_pause.")
            if kodi_library.pause_media(kodi_url, kodi_auth, headers):
                reply = "Media paused.  Resume playback by telling me to unpause."
            else:
                reply = "Nothing is playing right now."
            send_message_to_user(reply)
            continue

        # The user wants to unpause what's currently playing.
        if parsed_command["match"] == "commands_unpause":
            logging.debug("Matched commands_unpause.")
            if kodi_library.unpause_media(kodi_url, kodi_auth, headers):
                reply = "Media unpaused."
            else:
                reply = "Nothing is playing or paused right now."
            send_message_to_user(reply)
            continue

        # The user wants to stop what's currently playing.
        if parsed_command["match"] == "commands_stop":
            logging.debug("Matched commands_stop.")
            if kodi_library.stop_media(kodi_url, kodi_auth, headers):
                reply = "Media stopped."
            else:
                reply = "Nothing is playing right now."
            send_message_to_user(reply)
            continue

        # The user wants to ping Kodi.
        if parsed_command["match"] == "commands_ping":
            logging.debug("Matched commands_ping.")
            if kodi_library.ping_kodi(kodi_url, kodi_auth, headers):
                reply = "Kodi appears to be running and responsive."
            else:
                reply = "Kodi does not seem to be responding."
            send_message_to_user(reply)
            continue

        # The user wants to know what version of the API Kodi is running.
        if parsed_command["match"] == "commands_version":
            logging.debug("Matched commands_version.")
            tmp = kodi_library.get_api_version(kodi_url, kodi_auth, headers)
            if tmp:
                reply = "Kodi is running " + tmp + " of the JSON RPC API."
            else:
                reply = "I can't tell what version of the API Kodi is using."
            send_message_to_user(reply)
            continue

        # The user is asking what's playing at this moment.
        if parsed_command["match"] == "commands_whats_playing":
            logging.debug("Matched commands_whats_playing.")
            reply = kodi_library.whats_playing(kodi_url, kodi_auth, headers)
            send_message_to_user(str(reply))
            continue

        # If the user is asking the bot to start playback, figure out how to
        # do that.
        if parsed_command["match"] == "commands_play":
            logging.debug("Matched commands_play.")
            reply = "I think you're asking me to start playback.  Just a moment, please..."
            send_message_to_user(reply)

            # Case: Start playback of cached search results.
            # We don't seem to want to use the Songs database.
            # Check to see if there's an existing playlist #1.
            # If there isn't, create playlist #1.
            # Append each search result to playlist #1.
            # If music, call play_that_funky_music_white_boy with the playlist.
            # If video, call play_that_video with the playlist.

            # Figure out what the cached search results are - audio?  Video?
            # A playlist?
            # From that, call the proper playback method.

            # Case: Start playback of something the user knows exists on the
            # Kodi box.
            # Quietly run a search on the library to see if it exists.  Check
            # every part of the local database and go with the best match.
            # Go to "Start playback of cached search results."

    # Message queue not found.
    if request.status_code == 404:
        logger.info("Message queue %s does not exist." % bot_name)

    # Sleep for the configured amount of time.
    time.sleep(float(polling_time))

# Fin.
sys.exit(0)
