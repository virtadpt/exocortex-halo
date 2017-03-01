#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# systembot.py - Bot that periodically polls the state of the system it's
#   running on to see how healthy it is and alerts the owner via the XMPP
#   bridge if something's wrong.

# By: The Doctor <drwho at virtadpt dot net>
#       0x807B17C1 / 7960 1CDC 85C9 0B63 8D9F  DD89 3BD8 FF2B 807B 17C1

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
import argparse
import logging
import os
import psutil
import statvfs
import sys

# Constants.

# Global variables.
# Handle to an argument parser object.
argparser = None

# Handle to the parsed arguments.
args = None

# Path to a configuration file.
config_file = ""

# Handle to a configuration file parser.
config = None

# The "http://system:port/" part of the message digest URL.
server = ""

# Name of the construct.
bot_name = ""

# URL of the message queue to pull orders from.
message_queue = ""

# Loglevel to emit messages at.
config_log = ""

# Number of seconds in between pings to the message queue.
polling_time = 0

# Time (in seconds) between polling the various status markers.  This should be
# a fraction of the message queue poll time, perhaps 20-25%, with a hardwired
# value if it's too small (it would be four seconds or less, so default to five
# seconds?)
status_polling = 0

# Configuration for the logger.
loglevel = None

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
#   CPUs are idle as a floating point number.
def cpu_idle_time():
    return psutil.cpu_times_percent()[3]

# disk_usage(): Takes no arguments.  Returns a hash table containing the disk
#   device name as the key and percentage used as the value.
def disk_usage():
    disk_free = {}
    disk_partitions = None
    disk_device = None
    max = 0.0
    free = 0.0

    # Prime the hash with the names of the mounted disk partitions.
    disk_partitions = psutil.disk_partitions()
    for i in disk_partitions:
        disk_free[i.mountpoint] = ""

    # Calculate the maximum and free bytes of each disk device.
    for i in disk_free.keys():
        disk_device = os.statvfs(i)

        # blocks * bytes per block
        max = float(disk_device.f_blocks * disk_device.f_bsize)

        # blocks unused * bytes per block
        free = float(disk_device.f_bavail* disk_device.f_bsize)

        # Calculate bytes free as a percentage.
        disk_free[i] = (free / max) * 100

    return disk_free

# memory_utilization(): Function that returns the amount of memory free as a
#   floating point value (a percentage).  Takes no arguments.
def memory_utilization():
    return psutil.virtual_memory().percent

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

# Core code...
# Allocate a command-line argument parser.
argparser = argparse.ArgumentParser(description="A construct that monitors system statistics and sends alerts via the XMPP bridge in the event that things get too far out of whack.")

# Set the default config file and the option to set a new one.
argparser.add_argument('--config', action='store', 
    default='./system_bot.conf')

# Loglevels: critical, error, warning, info, debug, notset.
argparser.add_argument('--loglevel', action='store',
    help='Valid log levels: critical, error, warning, info, debug, notset.  Defaults to INFO.')

# Time (in seconds) between polling the message queues.
argparser.add_argument('--polling', action='store', default=60,
    help='Default: 60 seconds')

# Parse the command line arguments.
args = argparser.parse_args()
if args.config:
    config_file = args.config

# Read the options in the configuration file before processing overrides on the
# command line.
config = ConfigParser.ConfigParser()
if not os.path.exists(config_file):
    logging.error("Unable to find or open configuration file " +
        config_file + ".")
    sys.exit(1)
config.read(config_file)

# Get the URL of the message queue to contact.
server = config.get("DEFAULT", "queue")

# Get the name of the message queue to report to.
bot_name = config.get("DEFAULT", "bot_name")

# Construct the full message queue name.
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

# Set the loglevel from the override on the command line.
if args.loglevel:
    loglevel = set_loglevel(args.loglevel.lower())

# Configure the logger.
logging.basicConfig(level=loglevel, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Set the message queue polling time from override on the command line.
if args.polling:
    polling_time = args.polling

# Calculate how often the bot checks the system stats.  This is how often the
# main loop runs.
status_polling = polling_time / 4

# In debugging mode, dump the bot'd configuration.
logger.info("Everything is configured.")
logger.debug("Values of configuration variables as of right now:")
logger.debug("Configuration file: " + config_file)
logger.debug("Server to report to: " + server)
logger.debug("Message queue to report to: " + message_queue)
logger.debug("Bot name to respond to search requests with: " + bot_name)
logger.debug("Time in seconds for polling the message queue: " +
    str(polling_time))
logger.debug("Time in seconds for polling the system status: " +
    str(status_polling))

# Go into a loop in which the bot polls the configured message queue to see
# if it has any HTTP requests waiting for it.
logger.debug("Entering main loop to handle requests.")
while True:

    # If loop counter 








load = sysload()
print "One minute system load: " + str(load['one_minute'])
print "Five minute system load: " + str(load['five_minute'])
print "Fifteen minute system load: " + str(load['fifteen_minute'])
print
system_info = uname()
print "Hostname: " + system_info['hostname']
print "System architecture: " + system_info['arch']
print "System version: " + system_info['version']
print
print "Number of CPUs: " + str(cpus())
print
print "CPU idle percentage: " + str(cpu_idle_time())
print
disk_space = disk_usage()
for i in disk_space.keys():
    print "File system " + i + ": {:.2f}".format(disk_space[i]) + "% free"
print
print "Memory free: " + str(memory_utilization()) + "%"
print

# Fin.
sys.exit(0)

