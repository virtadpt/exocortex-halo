#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# help.py - Online help module for Kodi Bot.  All it does it return online help.
#   This might make it easier to internationalize this bot later, if it ever
#   comes to that.

# By: The Doctor <drwho at virtadpt dot net>
#       0x807B17C1 / 7960 1CDC 85C9 0B63 8D9F  DD89 3BD8 FF2B 807B 17C1

# License: GPLv3

# v1.1 - Adding and revising help text to make things easier.
#         - Got rid of the logging module because this module just returns
#           help text.
# v1.0 - Initial release.

# TO-DO:
# -

# Functions.
# help_basic(): Returns basic online help to the user as a string.  Takes the
#   bot's name and filename as arguments.
def help_basic(bot_name, bot_type):
    reply = """My name is %s, and I am an instance of %s.  I am a bot which interfaces with the Kodi open source media system.  I have a limited conversational interface that attempts to make sense out of what you ask me based upon a body of text called a corpus and statistical analysis.  If you want you can edit the corpus to better reflect how you type and even add new commands.  While I am not perfect I do want to do as well as I can with your help.

    I support general purpose Kodi commands, audio library specific commands, and video library specific commands.  You can ask for help with those, too.
    """ % (bot_name, bot_type)
    return reply

# help_commands(): Returns help about general commands the bot understands to
#   the user as a string.
def help_commands():
    reply = """I can pause, unpause, and stop what is currently playing.

    I can set the playback volume higher or lower, or to a specific level.  I can also mute and unmute playback.

    I can ping the Kodi server to make sure it's responding.  I can also ask it what version of the API it understands, for troubleshooting purposes.

    I can shut down and restart both Kodi and the server it's running on.

    I can help you search the audio and video libraries on the Kodi server.  I can do this by searching on titles, artists, genres, and names associated with those libraries.  I can start and stop playback of media.  If you have any playlists defined I can list and play those, too.

    Of course, I support party mode.  I wouldn't be very helpful if I didn't, would I?
    """
    return reply

# help_audio(): Returns help about audio related commands to the user as a
#   string.
def help_audio():
    reply = """I can search your audio collection by filename, title, artist, album, and genre.  I can play back any or all of what I find, skip forward and backward, and shuffle playback of what I find.  In case your library isn't well curated I'll make my best guess at playing what you ask me for based upon file and directory names but you'll need to be patient with me.
    """
    return reply

# help_video(): Returns help about video related commands to the user as a
#   string.
def help_video():
    reply = """I can search your video collection by filename, title, series, episode, and genre.  I can play back any or all of what I find, skip forward and backward, and shuffle playback of what I find.  In case your library isn't well curated I'll make my best guess at playing what you ask me for based upon file and directory names.  You'll need to be patient with me, though, because my best guess is just that - an educated guess.
    """
    return reply

if "__name__" == "__main__":
    pass
