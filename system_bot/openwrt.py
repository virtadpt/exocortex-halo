#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# openwrt.py - Module that makes it possible to use Systembot to monitor a
#   node running OpenWRT (https://openwrt.org/) when it's not feasible to do
#   a full install of Halo to it due to a lack of disk space.  This module
#   implements as many of the usual system monitoring features as possible
#   in as compatible a way as possible.  This module is not active by default.

# By: The Doctor <drwho at virtadpt dot net>
#       0x807B17C1 / 7960 1CDC 85C9 0B63 8D9F  DD89 3BD8 FF2B 807B 17C1

# License: GPLv3

# v1.2 - Added local time and date support.
# v1.1 - Added CPU counting support.
#      - Added CPU idle time support.
#      - Added disk usage support.
# v1.0 - Initial release.  Bare minimum for functional parity with regular
#   system monitoring (i.e, everything that's monitored automatically.)

# TO-DO:
# - temperature?
# - top?
# - system time

# Load modules.
import json
import logging
import math
import requests
import time

from datetime import timedelta

# Variables global to this module.
# Running lists of system averages.
one_minute_average = []
five_minute_average = []
fifteen_minute_average = []

# Functions.
# sysload(): Function that takes a snapshot of the current system load
#   averages.  Takes one argument, the base URL to the OpenWRT node.
#   Returns system loads as a hash table.
def sysload(openwrt_host):
    logging.debug("Entered function openwrt.sysload().")

    request = None
    system_info = {}
    sysload = {}

    #  Contact the OpenWRT host and get system info.
    request = requests.get(openwrt_host + "/cgi-bin/system/info")
    if not request:
        logging.err("Failed to contact endpoint " + openwrt_host + "/cgi-bin/system/info")
        sysload["one_minute"] = -1.0
        sysload["five_minute"] = -1.0
        sysload["fifteen_minute"] = -1.0
        return sysload

    # Extract the system load stats.
    system_info = json.loads(request.text)
    system_info = system_info["load"]

    # Due to the fact that OpenWRT does this strangely, we have to do some
    # math to get actual system load stats.  At least the 1, 5, and 15 minute
    # averages have stable positions.
    sysload["one_minute"] = round((system_info[0] / 65536.0), 2)
    sysload["five_minute"] = round((system_info[1] / 65536.0), 2)
    sysload["fifteen_minute"] = round((system_info[2] / 65536.0), 2)
    return sysload

# uname(): Function that collects uname information from the OpenWRT node.
#   This should  only be called upon request by the user.  Takes one argument,
#   the base URL to the OpenWRT node.  Returns a hash table containing system
#   information.
def uname(openwrt_host):
    logging.debug("Entered function openwrt.uname().")

    request = None
    sysinfo = {}
    system_info = {}

    #  Contact the OpenWRT host and get system info.
    request = requests.get(openwrt_host + "/cgi-bin/system/board")
    if not request:
        logging.err("Failed to contact endpoint " + openwrt_host + "/cgi-bin/system/board")
        system_info["hostname"] = "ERROR - unknown"
        system_info["version"] = "ERROR - unknown"
        system_info["buildinfo"] = "ERROR - unknown"
        system_info["arch"] = "ERROR - unknown"
        return system_info
    sysinfo = json.loads(request.text)

    # Extract the info we want.
    system_info["hostname"] = sysinfo["hostname"]
    system_info["version"] = sysinfo["kernel"]
    system_info["buildinfo"] = sysinfo["release"]["description"]
    system_info["arch"] = sysinfo["system"] + " (" + sysinfo["release"]["target"] + ") (" + sysinfo["board_name"] + ")"
    return system_info

# cpu_count(): Takes one argument, the base URL to the OpenWRT node.  Returns
#   the output of a cgi-bin script on the system or 0 if it didn't work.
def cpu_count(openwrt_host):
    logging.debug("Entered function openwrt.cpus().")
    request = None

    request = requests.get(openwrt_host + "/cgi-bin/system/cpu")
    if not request:
        logging.err("Failed to contact endpoint " + openwrt_host + "/cgi-bin/system/cpu")
        return 0
    return int(request.text)

# cpu_idle_time(): Takes one argument, the base URL to the OpenWRT node.
#   Returns the computed CPU idle time as a float or 0.0 if there was an error.
def cpu_idle_time(openwrt_host):
    logging.debug("Entered function openwrt.cpu_idle_time().")
    request = None

    request = requests.get(openwrt_host + "/cgi-bin/system/cpu_idle")
    if not request:
        logging.err("Failed to contact endpoint " + openwrt_host + "/cgi-bin/system/cpu_idle")
        return 0.0
    return float(request.text)

# get_disk_usage(): Takes no arguments.  Returns a hash table containing the
#   disk device name as the key and percentage used as the value.  This is
#   pretty involved, so it's a little more commented than most of the
#   utility functions in this module.
def get_disk_usage(openwrt_host):
    logging.debug("Entered function openwrt.get_disk_usage().")

    # "root" is /dev/root, which is always at 100%
    # "ubi" corresponds to sections of nvram that are overlaid onto /root,
    #   which hold system config variables.
    ignored = [ "root", "ubi" ]

    request = None
    raw_storage_stats = ""
    tmp_storage_stats = []
    storage_stats = []
    disk_used = {}

    # Get the disk usage stats from the OpenWRT device.
    request = requests.get(openwrt_host + "/cgi-bin/system/storage")
    if not request:
        logging.err("Failed to contact endpoint " + openwrt_host + "/cgi-bin/system/storage")
        disk_used["/"] = "unsupported"
        return disk_used
    raw_storage_stats = request.text
    tmp_storage_stats = raw_storage_stats.splitlines()

    # Get rid of the empty lines.  I can never remember how to do this..
    tmp_storage_stats = [x for x in tmp_storage_stats if x]
    for i in tmp_storage_stats:
        storage_stats.append(i.split())

    # Remove the lines in the array that we don't care about.
    for i in storage_stats:
        for j in ignored:
            if j in i[0]:
                storage_stats.remove(i)
                break
    logging.debug("Value of storage_stats: " + str(storage_stats))

    # Build the disk_used hash.
    for i in storage_stats:
        disk_used[i[-1]] = float(i[-2].replace("%", ""))
    logging.debug("Value of disk_used: " + str(disk_used))
    return disk_used

# memory_utilization(): Function that returns a snapshot of memory
#    utilization.  Takes one argument, the base URL to the OpenWRT node.
def memory_utilization(openwrt_host):
    logging.debug("Entered function openwrt.memory_utilization().")

    request = None
    memory_info = {}
    memory_stats = {}

    #  Contact the OpenWRT host and get system info.
    request = requests.get(openwrt_host + "/cgi-bin/system/info")
    if not request:
        logging.err("Failed to contact endpoint " + openwrt_host + "/cgi-bin/system/info")
        memory_stats["free"] = "ERROR - unknown"
        memory_stats["buffers"] = "ERROR - unknown"
        memory_stats["cached"] = "ERROR - unknown"
        return memory_stats

    memory_info = json.loads(request.text)
    memory_stats["free"] = memory_info["memory"]["free"]
    memory_stats["buffers"] = memory_info["memory"]["buffered"]
    memory_stats["cached"] = memory_info["memory"]["shared"]
    return memory_stats

# uptime(): Function that returns the length of time the system has been
#   online.  Takes one argument, the base URL to the OpenWRT node.
def uptime(openwrt_host):
    logging.debug("Entered function openwrt.uptime().")

    request = None
    uptime_seconds = {}

    #  Contact the OpenWRT host and get system info.
    request = requests.get(openwrt_host + "/cgi-bin/system/info")
    if not request:
        logging.err("Failed to contact endpoint " + openwrt_host + "/cgi-bin/system/info")
        return None
    uptime_seconds = json.loads(request.text)
    uptime_seconds = uptime_seconds["uptime"]
    return str(timedelta(seconds = uptime_seconds))

# get_logical_interfaces(): A function which builds a list of the logical
#   network interfaces on an OpenWRT syste.  Takes one argument, the URL to
#   the OpenWRT node.  Returns an array of strings or None.
def get_logical_interfaces(openwrt_host):
    logging.debug("Entered function openwrt.get_logical_interfaces().")

    request = None
    interfaces = {}
    nics = []

    #  Contact the OpenWRT host and dump the logical network interfaces
    request = requests.get(openwrt_host + "/cgi-bin/network/interface?dump")
    if not request:
        logging.err("Failed to contact endpoint " + openwrt_host + "/cgi-bin/network/interface?dump")
        return None
    interfaces = json.loads(request.text)

    # Iterate through the interfaces and pick out all the ones that aren't the
    # loopback.
    for i in interfaces["interface"]:
        if i["interface"] != "loopback":
            nics.append(i["interface"])
    logging.debug("List of interfaces found: " + str(nics))
    return nics

# local_ip_address(): Function that returns the local IP address of the system
#   by querying the primary network interface.  Takes one argument, the base
#   URL to the OpenWRT node.  Returns the IP address as a string or None if
#   it didn't work.
def local_ip_address(openwrt_host):
    logging.debug("Entered function openwrt.local_ip_address().")

    request = None
    nics = []
    primary_nic = None
    address = ""

    # Get a list of logical NICs on the host.
    nics = get_logical_interfaces(openwrt_host)
    if not nics:
        logging.warn("Couldn't get a list of network interfaces.  That's weird.")
        return None

    # Iterate through the list of network interfaces.
    for nic in nics:
        #  Contact the OpenWRT host and poll the interface.
        request = requests.get(openwrt_host + "/cgi-bin/network/interface?" + nic)
        if not request:
            logging.err("Failed to contact endpoint " + openwrt_host + "/cgi-bin/network/interface?" + nic)
            continue
        primary_nic = json.loads(request.text)

        # There is an assumption here which seems to hold for OpenWRT v18.04:
        # The WAN interface is the only one which has a primary_nic.route[] list
        # with a non-zero number of entries.  The semantics seem to be "the
        # default route."
        if len(primary_nic.route):
            logging.debug("Found primary network interface " + nic + ".")
            break
        else:
            logging.debug("The network interface " + nic + " does not seem to have the default route.")
            primary_nic = None

    # If primary_nic is still None, we didn't find any interfaces with a
    # default route.
    if not primary_nic:
        logging.warning("Did not find a network interface with a default route.  This is really strange.")
        return None

    # Extract the IP address of the primary NIC.
    address = primary_nic["route"][0]["source"].split("/")[0]
    logging.debug("I think the primary network interface is " + address + ".")
    return address

# convert_bytes(): Function that takes an arbitrary number of bytes and
#   converts them to kilobytes, megabytes, gigabytes... taken from here:
# https://stackoverflow.com/questions/5194057/better-way-to-convert-file-sizes-in-python
#   Written by user James Sapam, cleaned up a bit by me.  He did a better job
#   than I could.  Returns a string containing the appropriate suffix.
def convert_bytes(bytes):
    size_name = ("Bytes", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")

    # Catch the inactive interface case.
    if (bytes == 0):
        return "0B"

    # Extract the whole number part of the traffic volume.  This is the index
    # into size_name above.
    i = int(math.floor(math.log(bytes, 1024)))

    # 1024^i
    p = math.pow(1024, i)

    # Generate the fractional part of the traffic volume.
    s = round(bytes/p, 2)

    # return the number and the appropriate label for the number.
    return "%s %s" % (s, size_name[i])

# network_traffic(): Function that pulls stats for every online network
#   interface on the system (except for the loopback) and returns
#   them to the calling function.  Takes one argument, the base URL to the
#   OpenWRT node.
def network_traffic(openwrt_host):
    logging.debug("Entered function openwrt.network_traffic().")

    request = None
    nics = {}
    stats = {}

    # Get the list of physical NICs on the OpenWRT host.
    request = requests.get(openwrt_host + "/cgi-bin/network/device")
    if not request:
        logging.err("Failed to contact endpoint " + openwrt_host + "/cgi-bin/network/device")
        return None
    nics = json.loads(request.text)
    del nics["lo"]

    # Prime the network stats hash table with the remaining network
    # interfaces.  We make sure the network interfaces are marked as up.
    for i in list(nics.keys()):
        if nics[i]["up"]:
            stats[i] = {}

    # For every online interface, convert rx_bytes and tx_bytes into
    # human-readable strings.
    for i in list(nics.keys()):
        stats[i]["sent"] = convert_bytes(nics[i]["statistics"]["tx_bytes"])
        stats[i]["received"] = convert_bytes(nics[i]["statistics"]["rx_bytes"])
        logging.debug("Traffic volume to date for " + i + ": " + str(stats[i]))

    return stats

# local_datetime(): Function that queries the OpenWRT unit's current date
#   and time.  Takes one argument, the base URL to the OpenWRT node.  Returns
#   a string, the local date and time.
def local_datetime(openwrt_host):
    logging.debug("Entered function openwrt.local_datetime().")

    request = None
    system_info = {}
    local_time = None
    system_time = ""

    #  Contact the OpenWRT host and get system info.
    request = requests.get(openwrt_host + "/cgi-bin/system/info")
    if not request:
        logging.err("Failed to contact endpoint " + openwrt_host + "/cgi-bin/system/info")
        return None

    # Convert the current system time into a time struct.
    system_info = json.loads(request.text)
    local_time = time.localtime(system_info["localtime"])

    # Convert the time struct into an actual system time.
    system_time = time.strftime("%A, %d %B %Y %Z (UTC%z), %I:%M.%S %p",
        local_time)
    logging.debug("The remote node's system time is: " + system_time)
    return system_time

if "__name__" == "__main__":
    pass
