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
#   potentially manipulate them with commands sent by the bot's owner.  Use
#   the method psutil.test() to dump the process list and pick through it
#   looking for the stuff in question.

# Load modules.
import os
import psutil
import sys

# Constants.

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
# sysload(): Function that takes a snapshot of the current system load averages
#   and returns them as a hash table.  Takes no arguments.
def sysload():
    sysload = {}
    system_load = os.getloadavg()
    sysload['one_minute'] = system_load[0]
    sysload['five_minute'] = system_load[1]
    sysload['fifteen_minute'] = system_load[2]
    return sysload

# uname(): Function that calls os.uname(), extracts a few things, and returns
#   them as a hash table.  This should only be called upon request by the user,
#   or maybe when the bot starts up.  There's no sense in having it run every
#   time it loops because it changes so little.  Takes no arguments.
def uname():
    system_info = {}
    sysinfo = os.uname()
    system_info['hostname'] = sysinfo[1]
    system_info['version'] = sysinfo[2]
    system_info['buildinfo'] = sysinfo[3]
    system_info['arch'] = sysinfo[4]
    return system_info

# cpus(): Takes no arguments.  Returns the number of CPUs on the system.
def cpus():
    return psutil.cpu_count()

# cpu_idle_time(): Takes no arguments.  Returns the percentage of runtime the
#CPUs are idle as a floating point number.
def cpu_idle_time():
    return psutil.cpu_times_percent()[3]

# disk_usage(): Takes no arguments.  Returns a hash table containing the disk
#   device name as the key and percentage used as the value.
def disk_usage():
    disk_usage = {}

    disk_partitions = psutil.disk_partitions()
    for i in disk_partitions:
        disk_usage[i[0]] = ""

# memory_utilization(): Function that returns the amount of memory free as a
#   floating point value (a percentage).  Takes no arguments.
def memory_utilization():
    return psutil.virtual_memory().percent

# Core code...

# Fin.
sys.exit(0)
