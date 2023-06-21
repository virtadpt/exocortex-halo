#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# system_bot.py - Bot that periodically polls the state of the system it's
#   running on to see how healthy it is and alerts the owner via the XMPP
#   bridge if something's wrong.

# By: The Doctor <drwho at virtadpt dot net>
#       0x807B17C1 / 7960 1CDC 85C9 0B63 8D9F  DD89 3BD8 FF2B 807B 17C1

# License: GPLv3

# v4.7 - Ripped out the OpenWRT stuff because it's obsolete.  Use System
#        Script instead.
#      - Added some code to round off temperatures when requested by the user.
# v4.6 - Added a check and some code to pull file mounts to ignore from the
#        config file.  I added this because Certbot has to be installed as a
#        Snap to be supported on Ubuntu now, but by their nature they're
#        always at 100% of capacity, which means I get paged a few times an
#        hour.
# v4.5 - Made disk space usage messages easier to read by adding space used
#        and total space available.
#      - Made memory usage messages easier to understand, too.
# v4.4 - Added support for local date/time requests.
# v4.3 - Added support for remotely monitoring OpenWRT devices.
# v4.2 - Reworked the startup logic so that being unable to immediately
#        connect to either the message bus or the intended service is a
#        terminal state.  Instead, it loops and sleeps until it connects and
#        alerts the user appropriately.
# v4.1 - Added a command to query the busiest processes in the system (in
#       terms of CPU utilization).
# v4.0 - Ported to Python 3.
# v3.3 - Added a periodic check for all of the temperature sensors the psutil
#        module knows about.
#      - Added a command to query the current system temperature.
#      - Fixed a bug that prevented alerts from being sent.
#      - Tweaking the value of time_between_alerts because deliberate high
#        system loads can cause high CPU temperatures, which can result in
#        a constant stream of warnings.  I'll probably have to make this
#        variable configurable, instead.
#      - Renamed the call to system_stats.disk_usage() to use
#        system_stats.get_disk_usage() because it changed in that module.
#      - Reworked the free memory request to work with the reworked memory
#        functions in system_stats.py.
#      - Made check_memory_utilization() configurable.
# v3.2 - Changed "disk free" to "disk used," so that it's more like the output
#        of `df`.
# v3.1 - Added the ability to get the local IP of the host (not the public IP).
# v3.0 - Added real statistics support.  Parameterized stuff to eliminate some
#        magick numbers.
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
# - Add an "alert acknowledged" command that stops the bot from sending the
#   same alert every couple of seconds.  When the system state changes back to
#   normal, automatically flip the "alert acknowledged" flag back.

# Load modules.
import argparse
import configparser
import json
import logging
import os
import psutil
import requests
import sys
import time

import globals
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

# Number of standard deviations to consider hazardous to the system.
standard_deviations = 0

# Minimum and maximum lengths of the system stat queues.
minimum_length = 0
maximum_length = 0

# Configuration for the logger.
loglevel = None

# Used to determine when to poll the message queue.
loop_counter = 0

# Handle to a requests object.
request = None

# Command from the message queue.
command = ""

# Multiple of polling_time that must pass between sending alerts.  Defaults to
# 3600 seconds (one hour).
time_between_alerts = 3600

# Percentage of disk space used to consider critical.  Defaults to 90%.
disk_usage = 90.0

# Percentage of memory remaining to consider critical.  Defaults to 15%.
memory_remaining = 15.0

# Counters used to keep the bot from sending alerts too often.
sysload_counter = 0
cpu_idle_time_counter = 0
disk_usage_counter = 0
memory_utilization_counter = 0
memory_free_counter = 0
temperature_counter = 0

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
    headers = {"Content-type": "application/json"}

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

    # Start building the help message.
    message = message + """
    I continually monitor the state of the system I'm running on, and will send alerts any time an aspect deviates too far from normal if I am capable of doing so via the XMPP bridge."""

    # Continue building the help message.
    message = message + """
    I currently monitor system load, CPU idle time, disk utilization, and memory utilization.  The interactive commands I currently support are:

    help - Display this online help.
    load/sysload/system load - Get current system load.
    uname/info/system info - Get system info.
    cpus/CPUs - Get number of CPUs in the system.
    disk/disk usage/storage - Enumerate disk devices on the system and amount of storage used.
    memory/free memory/RAM/free ram - Amount of free memory.
    uptime - How long the system has been online, in days, hours, minutes, and seconds.
    IP address/public IP/IP addr/public IP address/addr - Current publically routable IP address of this host.
    IP/local IP/ local addr - Current (internal) IP of this host.
    network traffic/traffic volume/network stats/traffic stats/traffic count - Bytes sent and received per network interface.
    System temperature/system temp/temperature/temp/overheating/core temperature/core temp - Hardware temperature in Centigrade and Fahrenheit, if temperature sensors are enabled.
    top processes/busy processes/busiest processes - Top 5 busiest processes on the system.
    date/time/local date/local time/datetime/local datetime - Current date and time.

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

# Time (in seconds) in between sending warnings to the user.
argparser.add_argument("--time-between-alerts", action="store",
    help="Time in seconds in between sending warnings to the user.  This is to prevent getting flooded with alerts when a big job runs.")

# Parse the command line arguments.
args = argparser.parse_args()
if args.config:
    config_file = args.config

# Read the options in the configuration file before processing overrides on the
# command line.
config = configparser.ConfigParser()
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

# Get the time between alerts (in seconds) from the config file.
time_between_alerts = int(config.get("DEFAULT", "time_between_alerts"))

# Get the percentage of critical disk usage from the config file.
disk_usage = float(config.get("DEFAULT", "disk_usage"))

# See if there's a list of file system mounts to ignore in the configuration
# file, and if so read it in.
if config.has_section("file systems to ignore"):
    for i in config.options("file systems to ignore"):
        if "mount" in i:
            globals.ignored_mountpoints.append(config.get("file systems to ignore", i))

# Get the percentage of critical memory remaining from the config file.
memory_remaining = float(config.get("DEFAULT", "memory_remaining"))

# Get the number of standard deviations from the config file.
standard_deviations = config.get("DEFAULT", "standard_deviations")

# Get the minimum and maximum lengths of the stat queues from the config file.
minimum_length = config.get("DEFAULT", "minimum_length")
maximum_length = config.get("DEFAULT", "maximum_length")

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

# Set the time between system alerts if set on the command line.
if args.time_between_alerts:
    time_between_alerts = int(args.time_between_alerts)

# Calculate how often the bot checks the system stats.  This is how often the
# main loop runs.
status_polling = int(polling_time) / 4

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
logger.debug("Number of standard deviations: " + str(standard_deviations))
logger.debug("Minimum stat queue length: " + str(minimum_length))
logger.debug("Maximum stat queue length: " + str(maximum_length))
logger.debug("Value of polling_time (in seconds): " + str(polling_time))
if time_between_alerts == 0:
    logger.info("time_between_alerts is set to 0 - system alerting disabled!")
else:
    logger.debug("Value of time_between_alerts (in seconds): " + str(time_between_alerts))
logger.debug("Critical disk space usage: " + str(disk_usage))
logger.debug("Critical memory remaining: " + str(memory_remaining))
logger.debug("Value of loop_counter (in seconds): " + str(status_polling))
logger.debug("URL of web service that returns public IP address: " + ip_addr_web_service)
if len(processes_to_monitor):
    logger.debug("There are " + str(len(processes_to_monitor)) + " processes to watch over on the system.")
    for i in processes_to_monitor:
        print("    " + i[0])
if globals.ignored_mountpoints:
    logging.debug("File systems to ignore: %s" % globals.ignored_mountpoints)

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

# Go into a loop in which the bot polls the configured message queue to see
# if it has any HTTP requests waiting for it.
logger.debug("Entering main loop to handle requests.")
while True:

    # Reset the command from the message bus, just in case.
    command = ""

    # Start checking the system runtime stats.  If anything is too far out of
    # whack, send an alert via the XMPP bridge's response queue.
    sysload_counter = system_stats.check_sysload(sysload_counter,
        time_between_alerts, status_polling, standard_deviations,
        minimum_length, maximum_length, send_message_to_user)
    cpu_idle_time_counter = system_stats.check_cpu_idle_time(
        cpu_idle_time_counter, time_between_alerts, status_polling,
        send_message_to_user)
    disk_usage_counter = system_stats.check_disk_usage(disk_usage_counter,
        time_between_alerts, status_polling, disk_usage, send_message_to_user)
    memory_free_counter = system_stats.check_memory_utilization(
        memory_free_counter, time_between_alerts, status_polling,
        memory_remaining, send_message_to_user)
    temperature_counter = system_stats.check_hardware_temperatures(
        temperature_counter, time_between_alerts, status_polling,
        standard_deviations, minimum_length, maximum_length,
        send_message_to_user)

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

            # Basic system information.
            if command == "info":
                info = system_stats.uname()
                message = "System " + info["hostname"] + " in running kernel version " + info["version"] + " compiled by " + info["buildinfo"] + " on the " + info["arch"] + " processor architecture."
                send_message_to_user(message)

            # Number of CPUs on the system.
            if command == "cpus":
                info = system_stats.cpus()
                message = "The system has " + str(info) + " CPUs available to it."
                send_message_to_user(message)

            # Disk usage.
            if command == "disk":
                info = system_stats.get_disk_usage()
                message = "System disk space usage:\n"
                for key in list(info.keys()):
                    # Start a message line.
                    message = message + "\t" + key + " - ("

                    # Get disk usage (in bytes) for this device.
                    space = system_stats.get_disk_space(key)

                    # Add the disk space used to the message.
                    message = message + system_stats.convert_bytes(space["used"]) + " / "

                    # Add the total disk space.
                    message = message + system_stats.convert_bytes(space["total"]) + ")"

                    # Finish the message.
                    # /home - (xGB out of yTB) z.0% in use.
                    message = message + " - " + str("%.2f" % info[key]) + "% in use.\n"
                send_message_to_user(message)

            # Memory utilization.
            if command == "memory":
                info = system_stats.memory_utilization()
                logging.debug("value of info: " + str(info))

                # x GB / y GB (z%) memory in use.
                message = system_stats.convert_bytes(info.used)
                message = message + " / " + system_stats.convert_bytes(info.total)
                message = message + " (" + str(info.percent) + "%) memory in use.  "

                # a GB / y GB (b%)  free.
                message = message + system_stats.convert_bytes(info.free + info.buffers + info.cached)
                message = message + " / " + system_stats.convert_bytes(info.total)
                message = message + " (" + str(round(100.0 - info.percent, 2)) + "%) free."
                logging.debug("Value of message: " + str(message))
                send_message_to_user(message)

            # System uptime.
            if command == "uptime":
                info = system_stats.uptime()
                message = "The system has been online for " + info + "."
                send_message_to_user(message)

            # Public IP address.
            if command == "ip":
                info = system_stats.current_ip_address(ip_addr_web_service)
                message = "The system's current public IP address is " + info + "."
                send_message_to_user(message)

            # Local IP address.
            if command == "local ip":
                info = system_stats.local_ip_address()
                message = "The system's local IP address is " + info + "."
                send_message_to_user(message)

            # Network traffic stats per interface.
            if command == "traffic":
                info = system_stats.network_traffic()
                message = ""
                if not info:
                    message = "I was unable to get network traffic statistics."
                else:
                    for i in list(info.keys()):
                        message = message + "Network interface " + i + ":\n"
                        message = message + info[i]["sent"] + " sent.\n"
                        message = message + info[i]["received"] + " received.\n"
                        message = message + "\n"
                send_message_to_user(message)

            # System temperature.
            if command == "temperature":
                info = system_stats.get_hardware_temperatures()
                message = ""
                if not info:
                    message = "This system does not appear to have functioning temperature sensors.  This is common on virtual machines."
                else:
                    for sensor in list(info.keys()):
                        label = sensor
                        for device in info[sensor]:
                            # If the sensor has its own name, use that instead.
                            if device[0]:
                                label = device[0]

                            # Skip buggy sensors that return negative
                            # temperatures.
                            if device[1] <= 0.0:
                                continue

                            message = message + "Temperature sensor " + label + ": " + str(device[1]) + " degrees Centigrade (" + str(round(system_stats.centigrade_to_fahrenheit(device[1]), 2)) + " degrees Fahrenheit)\n"
                send_message_to_user(message)

            # Busiest running processes.
            if command == "processes":
                info = processes.get_top_processes()

                # Possible case: The CPU usage snapshot is taken when
                # everything is asleep, so CPU utilization is 0.0 across the
                # board, meaning there's an empty list.
                if not info:
                    message = "At this nanosecond, every process on the system has a CPU utilization of 0.0.  Everything's looking quiet."
                else:
                    message = "The busiest processes on the system are:\n\n"
                    for i in info:
                        message = message + str(i["pid"]) + "\t" + i["name"] + "\t" + str(i["cpu_percent"]) + "%\n"
                send_message_to_user(message)

            # Local date and time?
            if command == "datetime":
                info = system_stats.local_datetime()
                message = "The current date and time is: " + info
                send_message_to_user(message)

            # Fall-through.
            if command == "unknown":
                message = "I didn't recognize that command."
                send_message_to_user(message)

        # NOTE: We don't short-circuit all of the above checks with the
        # continue statement because we want the loop to fall down here every
        # time it runs to...
        # Reset loop counter.
        logger.debug("Resetting loop_counter.")
        loop_counter = 0

    # Bottom of loop.  Go to sleep for a while before running again.
    time.sleep(float(status_polling))

# Fin.
sys.exit(0)
