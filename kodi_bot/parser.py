#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# parser.py - Module for kodi_bot.py that implements all of the parsing
#   related functions.

# By: The Doctor <drwho at virtadpt dot net>
#       0x807B17C1 / 7960 1CDC 85C9 0B63 8D9F  DD89 3BD8 FF2B 807B 17C1

# License: GPLv3

# v1.0 - Initial release.

# TO-DO:
# -Make the online help interactive and subject based ("help video," "help
#   music.")

# Load modules.
import logging

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
# -
# -
# -
# -
# -
# -
# -
# -
# -

# parse_help(): Function that matches the word "help" all by itself in an input
#   string.  Returns the string "help" on a match and None if not.
def parse_help(command):
    try:
        parsed_command = help_command.parseString(command)
        return "help"
    except:
        return None

# parse_system_load(): Function that matches the strings "load" or "system load"
#   all by themselves in an input string.  Returns the string "load" on a match
#   and None if not.
def parse_system_load(command):
    try:
        parsed_command = load_or_system_load_command.parseString(command)
        return "load"
    except:
        return None

# parse_system_info(): Function that matches the strings "uname" or "system
#   info" or "info" all by themselves in an input string.  Returns the string
#   "info" on a match and None if not.
def parse_system_info(command):
    try:
        parsed_command = system_info_command.parseString(command)
        return "info"
    except:
        return None

# parse_cpus(): Function that matches the strings "cpus" or "CPUs" all by
#   themselves in an input string.  Returns the string "cpus" on a match and
#   None if not.
def parse_cpus(command):
    try:
        parsed_command = cpus_command.parseString(command)
        return "cpus"
    except:
        return None

# parse_disk_space(): Function that matches the strings "disk", "disk usage",
#   or "storage" all by themselves in an input string.  Returns the string
#   "disk" on a match and None if not.
def parse_disk_space(command):
    try:
        parsed_command = free_disk_space_command.parseString(command)
        return "disk"
    except:
        return None

# parse_free_memory(): Function that matches the strings "memory", "free
#   memory", "ram", or "free ram" all by themselves in an input string.
#   Returns the string "memory" on a match and None if not.
def parse_free_memory(command):
    try:
        parsed_command = unused_memory_command.parseString(command)
        return "memory"
    except:
        return None

# parse_uptime(): Function that matches the string "uptime" in an input
#   string.  Returns the string "uptime" on a match and None if not.
def parse_uptime(command):
    try:
        parsed_command = uptime_command.parseString(command)
        return "uptime"
    except:
        return None

# parse_ip_address(): Function that matches the strings "ip", "ip address",
#   "public ip", "ip addr", "public ip address", "addr".  Returns the string
#   "ip" on a match and None if not.
def parse_ip_address(command):
    try:
        parsed_command = ip_address_commands.parseString(command)
        return "ip"
    except:
        return None

# parse_network_traffic(): Function that matches the strings "network traffic",
#   "traffic volume", "network stats", "traffic stats", "traffic count".
#   Returns the string "traffic" on a match and None if not.
def parse_network_traffic(command):
    try:
        parsed_command = network_traffic_stats_command.parseString(command)
        return "traffic"
    except:
        return None

# parse_command(): Function that parses commands from the message bus.
#   Commands come as strings and are run through PyParsing to figure out what
#   they are.  A single-word string is returned as a match or None on no match.
#   Conditionals are short-circuited to speed up execution.
def parse_command(command):

    parsed_command = None

    # Clean up the incoming command.
    command = command.strip()
    command = command.strip('.')
    command = command.strip(',')
    command = command.lower()

    # If the get request is empty (i.e., nothing in the queue), bounce.
    if "no commands" in command:
        return None

    # Online help?
    parsed_command = parse_help(command)
    if parsed_command == "help":
        return parsed_command

    # System load?
    parsed_command = parse_system_load(command)
    if parsed_command == "load":
        return parsed_command

    # System info?
    parsed_command = parse_system_info(command)
    if parsed_command == "info":
        return parsed_command

    # CPUs?
    parsed_command = parse_cpus(command)
    if parsed_command == "cpus":
        return parsed_command

    # Free disk space?
    parsed_command = parse_disk_space(command)
    if parsed_command == "disk":
        return parsed_command

    # Free memory?
    parsed_command = parse_free_memory(command)
    if parsed_command == "memory":
        return parsed_command

    # System uptime?
    parsed_command = parse_uptime(command)
    if parsed_command == "uptime":
        return parsed_command

    # IP address?
    parsed_command = parse_ip_address(command)
    if parsed_command == "ip":
        return parsed_command

    # Network traffic stats?
    parsed_command = parse_network_traffic(command)
    if parsed_command == "traffic":
        return parsed_command

    # Fall-through: Nothing matched.
    return "unknown"

if "__name__" == "__main__":
    pass
