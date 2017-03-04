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
# - Make it possible to monitor specific processes running on the system, and
#   potentially manipulate them with commands sent by the bot's owner.  Use
#   the method psutil.test() to dump the process list and pick through it
#   looking for the stuff in question.
# - Make it possible to specify system stat thresholds in the config file
#   rather than hardcoding them.
# - Make it so that the bot stores previous system system values so that it
#   can compute standard deviations and alert if things change for the worse
#   too much.
# - Add an "alert acknowledged" command that stops the bot from sending the
#   same alert every couple of seconds.  When the system state changes back to
#   normal, automatically flip the "alert acknowledged" flag back.
# - Make the delay in between warning messages (which is currently polling_time
#   x20) configurable in the config file.

# Load modules.
import argparse
import ConfigParser
import json
import logging
import os
import psutil
import requests
import statvfs
import sys
import time

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

# Used to determine when to poll the message queue.
loop_counter = 0

# Handle to a requests object.
request = None

# Command from the message queue.
command = ""

# Multiple of polling_time that must pass between sending alerts.
time_between_alerts = 0

# Counters used to keep the bot from sending alerts too often.
sysload_counter = 0
cpu_idle_time_counter = 0
disk_usage_counter = 0
memory_utilization_counter = 0
memory_free_counter = 0

# Functions.
# sysload(): Function that takes a snapshot of the current system load averages
#   and returns them as a hash table.  Takes no arguments.
def sysload():
    logger.debug("Entered method sysload().")
    sysload = {}
    system_load = os.getloadavg()
    sysload['one_minute'] = system_load[0]
    sysload['five_minute'] = system_load[1]
    sysload['fifteen_minute'] = system_load[2]
    logger.debug("Current sysload values: " + str(sysload))
    return sysload

# check_sysload: Function that pulls the current system load and tests the
#   load averages to see if they're too high.  Sends a message to the bot's
#   owner if an average is too high.
def check_sysload(test=False):
    logger.debug("Entered method check_sysload().")

    message = ""
    if test:
        current_load_avg = {}
        current_load_avg['one_minute'] = 5.0
        current_load_avg['five_minute'] = 5.0
        current_load_avg['fifteen_minute'] = 5.0
    else:
        current_load_avg = sysload()

    # Check the average system loads and construct a message for the bot's
    # owner.
    if current_load_avg['one_minute'] >= 1.5:
        message = message + "WARNING: The current system load is " + str(current_load_avg['one_minute']) + ".\n"

    if current_load_avg['five_minute'] >= 2.0:
        message = message + "WARNING: The five minute system load is " + str(current_load_avg['one_minute']) + ".  What's running that's doing this?\n"

    if current_load_avg['fifteen_minute'] >= 2.0:
        message = message + "WARNING: The fifteen minute system load is " + str(current_load_avg['one_minute']) + ".  I think something's wrong.\n"

    # In test mode, just return the message.
    if test:
        return message

    # If a message has been constructed, check to see if it's been longer than
    # the last time a message was sent.  If so, send it and reset the counter.
    if message:
        if sysload_counter >= time_between_alerts:
            send_message_to_user(message)
            sysload_counter = 0
            return

        # If enough time between alerts hasn't passed yet, just increment the
        # counter.
        sysload_counter = sysload_counter + status_polling
    return

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

# check_cpu_idle_time(): Takes no arguments.  Sends an alert to the bot's owner
#   if the CPU idle time is too low.
def check_cpu_idle_time(test=False):
    logger.debug("Entered method check_cpu_idle_time().")

    message = ""
    idle_time = cpu_idle_time()

    # If the bot is in self-test mode, set idle_time to a critical value.
    if test:
        idle_time = 0.01

    # Check the percentage of CPU idle time and construct a message for the
    # bot's owner if it's too low.
    if idle_time < 15.0:
        message = "WARNING: The current CPU idle time is sitting at " + str(idle_time) + ".  What's keeping it so busy?"

    # In self-test mode, return the message.
    if test:
        return message

    # If a message has been built, check to see if enough time in between
    # messages has passed.  If so, send the message.
    if message:
        if cpu_idle_time_counter >= time_between_alerts:
            send_message_to_user(message)
            cpu_idle_time_counter = 0
            return

        # If not enough time has passed yet, just increment the counter.
        cpu_idle_time_counter = cpu_idle_time_counter + status_polling
    return

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

# check_disk_usage(): Pull the amount of free storage for each disk device on
#   the system and send the bot's owner an alert if one of the disks gets too
#   full.
def check_disk_usage(test=False):
    logger.debug("Entered method check_disk_usage().")
    message = ""
    disk_space_free = disk_usage()

    # If bot is in self-test mode, set the value of disk_space_free to a
    # critical value.
    if test:
        disk_space_free = {}
        disk_space_free['/boot'] = 0.01
        disk_space_free['/'] = 0.01

    # Check the amount of space free on each disk device.  For each disk that's
    # running low on space construct a line of the message.
    for disk in disk_space_free.keys():
        if disk_space_free[disk] < 20.0:
            message = message + "WARNING: Disk device " + disk + " has " + str(disk_space_free[disk]) + "% of its capacity left.\n"

    # If bot is in self-test mode, return the message.
    if test:
        return message

    # If a message has been constructed, check how much time has passed since
    # the last message was sent.  If enough time has, sent the bot's owner
    # the message.
    if message:
        if disk_usage_counter >= time_between_alerts:
            send_message_to_user(message)
            disk_usage_counter = 0
            return

        # Not enough time has passed.  Increment the counter and move on.
        disk_usage_counter = disk_usage_counter + status_polling
    return

# memory_utilization(): Function that returns the amount of memory free as a
#   floating point value (a percentage).  Takes no arguments.
def memory_utilization():
    return psutil.virtual_memory().percent

# check_memory_utilization(): Function that checks how much memory is free on
#   the system and alerts the bot's owner if it's below a certain amount.
def check_memory_utilization(test=False):
    logger.debug("Entered method check_memory_utilization().")
    message = ""
    memory_free = memory_utilization()

    # If the bot is in self-test mode, set memory_free to a critical value.
    if test:
        memory_free = 0.01

    # Check the amount of memory free.  If it's below a critical threshold
    # construct a message for the bot's owner.
    if memory_free <= 20.0:
        message = "WARNING: The amount of free memory has reached the critical point of " + str(memory_free) + "% free.  You'll want to see to this before the OOM killer starts reaping processes."

    # If the bot is in self-test mode, return the message.
    if test:
        return message

    # If a message has been constructed, check how much time has passed since
    # the last message was sent.  If enough time has, send the bot's owner the
    # message.
    if message:
        if memory_free_counter >= time_between_alerts:
            send_message_to_user(message)
            memory_free_counter = 0
            return

        # Not enough time has passed.  Increment the counter and move on.
        memory_free_counter = memory_free_counter + status_polling
    return

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
    logger.debug("Entered function send_message_to_user().")

    # Headers the XMPP bridge looks for for the message to be valid.
    headers = {'Content-type': 'application/json'}

    # Set up a hash table of stuff that is used to build the HTTP request to
    # the XMPP bridge.
    reply = {}
    reply['name'] = bot_name
    reply['reply'] = message

    # Send an HTTP request to the XMPP bridge containing the message for the
    # user.
    request = requests.put(server + "replies", headers=headers,
        data=json.dumps(reply))
    return

# parse_command(): Function that parses commands from the message bus.
#   Commands are of the form MOOF MOOF MOOF.
def parse_command(command):
    logger.debug("Entered method parse_command().")

    # Clean up the get request.
    get_request = get_request.strip()
    get_request = get_request.strip('.')

    # If the get request is empty (i.e., nothing in the queue), bounce.
    if "no commands" in get_request:
        logger.debug("Got empty get request.")
        return

    return

# run_self_tests(): Function that calls each check function in succession and
#   prints the output.  It then calls each check function and deliberately
#   triggers the warning conditions to make sure they work.
def run_self_tests():
    print "Exercising sysload functions."
    print sysload()
    print check_sysload(test=True)

    print "Exercising uname()."
    print uname()
    print

    print "Exercising cpus()."
    print cpus()
    print

    print "Exercising cpu_idle_time() functions."
    print cpu_idle_time()
    print check_cpu_idle_time(test=True)
    print

    print "Exercising disk_usage() functions."
    print disk_usage()
    print check_disk_usage(test=True)

    print "Exercising memory_utilization() functions."
    print memory_utilization()
    print check_memory_utilization(test=True)
    print

    return

# Core code...
# Allocate a command-line argument parser.
argparser = argparse.ArgumentParser(description="A construct that monitors system statistics and sends alerts via the XMPP bridge in the event that things get too far out of whack.")

# Set the default config file and the option to set a new one.
argparser.add_argument("--config", action="store", 
    default="./system_bot.conf")

# Loglevels: critical, error, warning, info, debug, notset.
argparser.add_argument("--loglevel", action="store",
    help="Valid log levels: critical, error, warning, info, debug, notset.  Defaults to INFO.")

# Time (in seconds) between polling the message queues.
argparser.add_argument("--polling", action="store", default=60,
    help="Default: 60 seconds")

# Trigger the self-test function?
argparser.add_argument("--test", action="store_true",
    help="Perform a self-test of the bot's trigger conditions for testing and debugging.  The bot will terminate afterward.")

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

# Calculate the period of time that should pass in between sending alerts to
# the user to keep from inundating them.
time_between_alerts = polling_time * 20

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

# Determine if the bot is going into self-test mode, and if so execute the
# self-tests.
if args.test:
    logger.info("Executing bot self-test.")
    run_self_tests()
    sys.exit(31337)

# Go into a loop in which the bot polls the configured message queue to see
# if it has any HTTP requests waiting for it.
logger.debug("Entering main loop to handle requests.")
while True:
    # Reset the command from the message bus, just in case.
    command = ""

    # Start checking the system runtime stats.  If anything is too far out of
    # whack, send an alert via the XMPP bridge's response queue.
    check_sysload()
    check_cpu_idle_time()
    check_disk_usage()
    check_memory_utilization()

    # Add status_polling to loop counter.
    loop_counter = loop_counter + status_polling

    # If loop_counter is equal to polling_time, check the message queue for
    # commands.
    if loop_counter >= polling_time:
        try:
            logger.debug("Contacting message queue: " + message_queue)
            request = requests.get(message_queue)
            logger.debug("Response from server: " + request.text)
        except:
            logger.warn("Connection attempt to message queue timed out or failed.  Going back to sleep to try again later.")
            time.sleep(float(polling_time))
            continue

        # Test the HTTP response code.
        # Success.
        if request.status_code == 200:
            logger.debug("Message queue " + bot_name + " found.")

            # Extract the command.
            command = json.loads(request.text)
            logger.debug("Command from user: " + str(command))

            # Parse the command.
            command = parse_command(command)
            logger.debug("Parsed command: " + str(page_request))

            # If there was no page request, go back to sleep.
            if not page_request:
                time.sleep(float(polling_time))
                continue

        # Reset loop counter.
        loop_counter = 0

    # Bottom of loop.  Go to sleep for a while before running again.
    time.sleep(float(status_polling))

# Fin.
sys.exit(0)

