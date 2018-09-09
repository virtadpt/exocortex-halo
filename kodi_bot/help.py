#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# help.py - Online help module for Kodi Bot.  All it does it return online help.
#   This might make it easier to internationalize this bot later, if it ever
#   comes to that.

# By: The Doctor <drwho at virtadpt dot net>
#       0x807B17C1 / 7960 1CDC 85C9 0B63 8D9F  DD89 3BD8 FF2B 807B 17C1

# License: GPLv3

# v1.0 - Initial release.

# TO-DO:
# -

# Load modules.
import logging

# Functions.
# help_basic(): Returns basic online help to the user as a string.  Takes the
#   bot's name and filename as arguments.
def help_basic(bot_name, bot_type):
    reply = """My name is %s, and I am an instance of %s.  I am a bot which interfaces with the Kodi open source media system.  I have a limited conversational interface that attempts to make sense out of what you ask me based upon a body of text called a corpus and statistical analysis.  If you want you can edit the corpus to better reflect how you type and even add new commands.

    I support general purpose Kodi commands, audio library specific commands, and video library specific commands.  You can ask for help with those, too.
    """ % (bot_name, bot_type)
    return reply

# help_commands(): Returns help about general commands the bot understands to
#   the user as a string.
def help_commands():
    return reply

# help_audio(): Returns help about audio related commands to the user as a
#   string.
def help_audio():
    return reply

# help_video(): Returns help about video related commands to the user as a
#   string.
def help_video():
    return reply

if "__name__" == "__main__":
    pass
