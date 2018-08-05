#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# system_bot.py - Bot that periodically polls the state of the system it's
#   running on to see how healthy it is and alerts the owner via the XMPP
#   bridge if something's wrong.

# By: The Doctor <drwho at virtadpt dot net>
#       0x807B17C1 / 7960 1CDC 85C9 0B63 8D9F  DD89 3BD8 FF2B 807B 17C1

# License: GPLv3

# v2.3 - Added capability to monitor and restart processes if they die.
#      - Removed the self test function.  That didn't do anything, anyway.
# v2.2 - Added function to get public IP address of host.
#      - Added function that gets network traffic stats.
# v2.1 - Added uptime.
# v2.0 - Refactoring code to split it out into separate modules.
# v1.0 - Initial release.

# TO-DO:
# - Make it possible to specify arbitrary commands in the config file that the
#   bot can be ordered to execute.
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
import pyparsing as pp
import requests
import sys
import time

import parser
import processes
import system_stats

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

# A list of processes on the system to monitor.  Can be empty.
processes_to_monitor = []

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

# List of dead processes on the system.  If it's ever populated something died
# and needs attended to.
dead_processes = None

# URL of web service that just returns the IP address of the host.
ip_addr_web_service = ""

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

    # Headers the XMPP bridge looks for for the message to be valid.
    headers = {'Content-type': 'application/json'}

    # Set up a hash table of stuff that is used to build the HTTP request to
    # the XMPP bridge.
    reply = {}
    reply["name"] = bot_name
    reply["reply"] = message

    # Send an HTTP request to the XMPP bridge containing the message for the
    # user.
    request = requests.put(server + "replies", headers=headers,
        data=json.dumps(reply))
    return

# online_help(): Function that returns text - online help - to the user.  Takes
#   no arguments, returns a complex string.
def online_help():
    logger.debug("Entered the function online_help().")
    message = "My name is " + bot_name + " and I am an instance of " + sys.argv[0] + ".\n"
    message = message + """
    I continually monitor the state of the system I'm running on, and will send alerts any time an aspect deviates too far from normal if I am capable of doing so via the XMPP bridge.  I currently monitor system load, CPU idle time, disk utilization, and memory utilization.  The interactive commands I currently support are:

    help - Display this online help.
    load/sysload/system load - Get current system load.
    uname/info/system info - Get system info.
    cpus/CPUs - Get number of CPUs in the system.
    disk/disk usage/storage - Enumerate disk devices on the system and amount of storage free.
    memory/free memory/RAM/free ram - Amount of free memory.
    uptime - How long the system has been online, in days, hours, minutes, and seconds.
    IP/IP address/public IP/IP addr/public IP address/addr - Current publically routable IP address of this host.
    network traffic/traffic volume/network stats/traffic stats/traffic count - Bytes sent and received per network interface.

    All commands are case-insensitive.
    """
    return message

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
argparser.add_argument("--polling", action="store", help="Default: 60 seconds")

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

# Get the URL of the web service that just returns an IP address.
try:
    ip_addr_web_service = config.get("DEFAULT", "ip_addr_site")
except:
    logging.error("You need to specify a URL to a web service that only returns an IP address when you hit it.  There should be one in the configuration file.  If not, you might need a new copy of the config file because a directive is missing.")
    sys.exit(1)

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
status_polling = int(polling_time) / 4

# Calculate the period of time that should pass in between sending alerts to
# the user to keep from inundating them.
time_between_alerts = polling_time * 20

# See if there's a list of processes to monitor in the configuration file, and
# if so read it into the list.
if config.has_section("processes to monitor"):
    for i in config.options("processes to monitor"):
        if "process" in i:
            processes_to_monitor.append(config.get("processes to monitor", i).split(','))

# In debugging mode, dump the bot'd configuration.
logger.info("Everything is configured.")
logger.debug("Values of configuration variables as of right now:")
logger.debug("Configuration file: " + config_file)
logger.debug("Server to report to: " + server)
logger.debug("Message queue to report to: " + message_queue)
logger.debug("Bot name to respond to search requests with: " + bot_name)
logger.debug("Value of polling_time (in seconds): " + str(polling_time))
logger.debug("Value of loop_counter (in seconds): " + str(status_polling))
logger.debug("URL of web service that returns public IP address: " + ip_addr_web_service)
if len(processes_to_monitor):
    logger.debug("There are " + str(len(processes_to_monitor)) + " processes to watch over on the system.")
    for i in processes_to_monitor:
        print "    " + i[0]

# Go into a loop in which the bot polls the configured message queue to see
# if it has any HTTP requests waiting for it.
logger.debug("Entering main loop to handle requests.")
send_message_to_user(bot_name + " now online.")
while True:

    # Reset the command from the message bus, just in case.
    command = ""

    # Start checking the system runtime stats.  If anything is too far out of
    # whack, send an alert via the XMPP bridge's response queue.
    sysload_counter = system_stats.check_sysload(sysload_counter,
        time_between_alerts, status_polling)
    cpu_idle_time_counter = system_stats.check_cpu_idle_time(
        cpu_idle_time_counter, time_between_alerts, status_polling)
    disk_usage_counter = system_stats.check_disk_usage(disk_usage_counter,
        time_between_alerts, status_polling)
    memory_free_counter = system_stats.check_memory_utilization(
        memory_free_counter, time_between_alerts, status_polling)

    # Increment loop_counter by status_polling.  Seems obvious, but this makes
    # it easy to grep for.
    loop_counter = loop_counter + status_polling

    # If loop_counter is equal to polling_time, and there are any processes to
    # monitor, look for them.
    if int(loop_counter) >= int(polling_time) and processes_to_monitor:
        dead_processes = processes.check_process_list(processes_to_monitor)
        if dead_processes:
            message = "WARNING: The following monitored processes seem to have crashed:\n"
            for i in dead_processes:
                message = message + i[0] + "\n"
            message = message + "I am now attempting to restart them."
            send_message_to_user(message)
            dead_processes = processes.restart_crashed_processes(dead_processes)

        # At this point in the check, if there are any dead processes, they
        # didn't restart and something went wrong.
        if dead_processes:
            message = "WARNING: The following crashed processes could not be restarted:\n"
            for i in dead_processes:
                message = message + i[0] + "\n"
            message = message + "You need to log into the server and restart them manually."
            send_message_to_user(message)

    # If loop_counter is equal to polling_time, check the message queue for
    # commands.
    if int(loop_counter) >= int(polling_time):
        try:
            logger.debug("Contacting message queue: " + message_queue)
            request = requests.get(message_queue)
            logger.debug("Response from server: " + request.text)
        except:
            logger.warn("Connection attempt to message queue timed out or failed.  Going back to sleep to try again later.")
            time.sleep(float(status_polling))
            continue

        # Test the HTTP response code.
        # Success.
        if request.status_code == 200:
            logger.debug("Message queue " + bot_name + " found.")

            # Extract the command.
            command = json.loads(request.text)
            logger.debug("Command from user: " + str(command))
            command = command["command"]
            if not command:
                logger.debug("Empty command.")
                logger.debug("Resetting loop_counter.")
                loop_counter = 0
                time.sleep(float(polling_time))
                continue

            # Parse the command.
            command = parser.parse_command(command)
            logger.debug("Parsed command: " + str(command))

            # If the user is requesting online help...
            if command == "help":
                send_message_to_user(online_help())

            # If the user is requesting system load...
            if command == "load":
                load = system_stats.sysload()
                message = "The current system load is " + str(load["one_minute"]) + " on the one minute average and " + str(load["five_minute"]) + " on the five minute average."
                send_message_to_user(message)

            if command == "info":
                info = system_stats.uname()
                message = "System " + info["hostname"] + " in running kernel version " + info["version"] + " compiled by " + info["buildinfo"] + " on the " + info["arch"] + " processor architecture."
                send_message_to_user(message)

            if command == "cpus":
                info = system_stats.cpus()
                message = "The system has " + str(info) + " CPUs available to it."
                send_message_to_user(message)

            if command == "disk":
                info = system_stats.disk_usage()
                message = "The system has the following amounts of disk space free:\n"
                for key in info.keys():
                    message = message + "\t" + key + " - " + str("%.2f" % info[key]) + "%\n"
                send_message_to_user(message)

            if command == "memory":
                info = system_stats.memory_utilization()
                message = str(info) + "% of the system memory is free."
                send_message_to_user(message)

            if command == "uptime":
                info = system_stats.uptime()
                message = "The system has been online for " + info + "."
                send_message_to_user(message)

            if command == "ip":
                info = system_stats.current_ip_address(ip_addr_web_service)
                message = "The system's current public IP address is " + info + "."
                send_message_to_user(message)

            if command == "traffic":
                info = system_stats.network_traffic()
                message = ""
                if not info:
                    message = "I was unable to get network traffic statistics."
                else:
                    for i in info.keys():
                        message = message + "Network interface " + i + ":\n"
                        message = message + info[i]["sent"] + " sent.\n"
                        message = message + info[i]["received"] + " received.\n"
                        message = message + "\n"
                send_message_to_user(message)

            if command == "unknown":
                message = "I didn't recognize that command."
                send_message_to_user(message)

        # Reset loop counter.
        logger.debug("Resetting loop_counter.")
        loop_counter = 0

    # Bottom of loop.  Go to sleep for a while before running again.
    time.sleep(float(status_polling))

# Fin.
sys.exit(0)
