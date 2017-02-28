#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# systembot.py - Bot that periodically polls the state of the system it's
#   running on to see how healthy it is and alerts the owner via the XMPP
#   bridge if something's wrong.

# By: The Doctor <drwho at virtadpt dot net>

# License: GPLv3

# v1.0 - Initial release.

# TO-DO:
# - Make it possible to specify arbitrary commands in the config file that the
#   bot can be ordered to execute.
# - Put the full paths into /proc for the various system state variables into
#   the configuration file, and not hardcoded.
# - Make it possible to monitor specific processes running on the system, and
#   potentially manipulate them with commands sent by the bot's owner.

# Load modules.
import os
import sys

# Constants.
# Full path to the system load.
loadavg = "/proc/loadavg"

# Full path to memory utilization stats.
meminfo = "/proc/meminfo"

# Disk usage stats.
diskstats = "/proc/diskstats"

# Number of currently logged in users.

# Number of running processes.

# Global variables.
# Time (in seconds) between polling the message queue.

# Time (in seconds) between polling the various status markers.  This should be
# a fraction of the message queue poll time, perhaps 20-25%, with a hardwired
# value if it's too small (it would be four seconds or less, so default to five
# seconds?)

# If this is a class or module, say what it is and what it does.

# Classes.

# Functions.

# Core code...

# Fin.
sys.exit(0)
