#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# parser.py - Module for kodi_bot.py that implements the command parser.

# By: The Doctor <drwho at virtadpt dot net>
#       0x807B17C1 / 7960 1CDC 85C9 0B63 8D9F  DD89 3BD8 FF2B 807B 17C1

# License: GPLv3

# v1.0 - Initial release.

# TO-DO:
# - Make the online help interactive and subject based ("help video," "help
#   music.")
# - Normalize the corpora to lowercase at load-time.

# Load modules.
import logging
import os
import sys

from fuzzywuzzy import fuzz

# Commands to support:
# - List all known media sources: video, pictures, music
#   This is probably a helper method: The output will be used by other methods.
#   Do this on startup and cache the results.
#   Files.GetSources()
# - List a particular media source: video, pictures, music
#   Only support media sources found earlier/above.
# - Build an internal list of media files on the Kodi box.
#   Files.GetDirectory()
#   Used by other methods to support searching for the presence of certain
#   things.  Maybe normalize everything?  Find a Python module that's good at
#   this sort of thing?
# - Search the Kodi box's library:
#   "Do I have any music by...?"
#   "Do I have any videos with...?"
#   "Do I have a song named...?"
# - List known playlists.
#   This is probably going to be a utility method.
#   Playlist.GetPlaylists()
# - Trigger playback of an existing playlist.
#   Use cached list of playlists?
#   Playlist.GetItems()
# - See if Kodi is online.  Maybe do this periodically?
#   JSONRPC.Ping()
# - Ask what version of the JSON-RPC API is being used on the Kodi box.
#   JSONRPC.Version()
# - Display a message on the Kodi box's screen.
#   GUI.ShowNotification()
# - Shut down Kodi.
#   System.Shutdown()
# - Restart Kodi.
#   System.Reboot()
# - Find out if something is playing, and if so what it is (video, audio).
#   This is a helper method.
#   Player.GetActivePlayers()
# - Build a list of usable players in the Kodi instance.
#   Players.GetPlayers()
#   Cache the output.  Need both the type and the ID code, because Kodi uses
#   the ID codes as identifiers.
# - Initiate/terminate party mode.
#   Player.SetPartymode([ID number of audio player], [True, False])
# - Pause/unpause playback.
#   Player.PlayPause([0, 1])
# - "What is currently playing?"
#   "What's currently playing?"
#   Find out what is currently playing with Player.GetActivePlayers().  Then,
#   Player.GetItem([ID code of running player])
# - Figure out how to specify, in broad strokes, what you want to listen to.
#   "Play the sisters of mercy."
#   "Play information society."
#   "Play an episode of foo."
#   "Play some art bell."
#   "Play Floodland."
#   "Shuffle Floodland."
#   The media type/filetype will be used to pick the media player type to use.
#   Get a list of artists with AudioLibrary.GetArtists()
#   ...map what the user is asking for to the contents of that list.  This might
#   need to be a fuzzy match.  I don't yet know how to do this.
# - Stop what is currently playing.
#   Find out what is currently playing with Player.GetActivePlayers().  Then,
#   Player.Stop([ID code of running player])
# - Update Kodi's databases.
#   [Audio,Video]Library.Scan()
#   Then rebuild the bot's internal indices?
# -
#
# What the parser returns:
# - No match? None.
# - Match?
#   parsed_command = {}
#   parsed_command["confidence"] = confidence in match
#   parsed_command[""]

# load_corpora(): Trains the command parser on a list of corpora.  Takes two
#   arguments, a string that points to a directory full of text corpora, and a
#   hash of command types.  Returns a hash of command types containing the
#   corpora to match against.
def load_corpora(corpora_dir, command_types):
    logging.debug("Entered parser.load_corpora().")

    command_type = ""

    corpora_dir = os.path.abspath(corpora_dir)
    for filename in os.listdir(corpora_dir):
        logging.debug("Looking at corpus file %s." % filename)

        # Generate the key for the hash.
        command_type = filename.strip(".txt")

        # Test the length of the corpus file.  If it's 0, then skip the command
        # class.
        filename = os.path.join(corpora_dir, filename)
        if not os.path.getsize(filename):
            logging.warn("Corpus filename %s has a length of zero bytes.  Skipping this command class." % filename)
            command_types.pop(command_type)
            continue

        # Read the contents of the corpus file in.
        try:
            with open(filename, "r") as file:
                command_types[command_type] = file.read().splitlines()
        except:
            logging.warn("Unable to open filename %s.  Skipping command class." % os.path.join(corpora_dir, filename))
            command_types.pop(command_type)

    logging.debug("Recognized command types: %s" % str(command_types.keys()))
    return command_types

# parse(): Function that parses commands from the message bus.  Takes MOOF args,
#   the command to parse, a hash containing corpora to match against, and the
#   type of command to match against.  A hash table with the best match is
#   returned as a match or None on no match.
def parse(command, possible_commands):
    logging.debug("Entered parser.parse().")

    parsed_command = {}
    parsed_command["confidence"] = 0
    parsed_command["match"] = ""

    # Clean up the incoming command.
    command = command.strip()
    command = command.strip('.')
    command = command.strip(',')
    command = command.lower()

    # If the get request is empty (i.e., nothing in the queue), bounce.
    if "no commands" in command:
        return None

    # Walk through the command corpora and see which one most closely matches.
    for command_type in possible_commands.keys():
        logging.debug("Now matching against command class %s." % command_type)

        for i in possible_commands[command_type]:
            tmp = fuzz.token_sort_ratio(command, i.lower())
            if tmp > parsed_command["confidence"]:
                logging.debug("Replacing match with one of a higher confidence:")
                logging.debug("New match: %s" % i)
                logging.debug("Confidence of new match: %d" % tmp)
                parsed_command["confidence"] = tmp
                parsed_command["match"] = command_type

    return parsed_command

if "__name__" == "__main__":
    pass
