#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# system_stats.py - Module that implements all of the system statistic
#   collection and reporting parts of system_bot.py.

# By: The Doctor <drwho at virtadpt dot net>
#       0x807B17C1 / 7960 1CDC 85C9 0B63 8D9F  DD89 3BD8 FF2B 807B 17C1

# License: GPLv3

# v4.0 - Ported to Python 3.
# v3.3 - Added a Centigrade-to-Fahrenheit utility function.
#      - Added a function that periodically checks the current temperature
#        of every sensor on the system and sends an alert to the user if
#        the temperature reaches what the driver considers a dangerous or
#        critical point.
#      - Renamed disk_usage() to get_disk_usage() because it conflicted
#        with a variable name elsewhere.
#      - Made check_memory_utilization() configurable.
# v3.2 - Changed "disk free" to "disk used," so it's more like the output of.
#        `df`.
# v3.1 - Added function to get the local IP address of the host.
# v3.0 - Added real statistics support.
# v2.2 - Added function to get public IP address of host.
#      - Added function that gets network traffic stats.
# v2.1 - Added system uptime.
# v2.0 - Refactoring code to split it out into separate modules.
# v1.0 - Initial release.

# TO-DO:
# - Optimize the temperature monitoring loop for the general case.

# Load modules.
import logging
import math
import os
import psutil
import requests
import statistics
import sys

from datetime import timedelta

# Variables global to this module.
# Running lists of system averages.
one_minute_average = []
five_minute_average = []
fifteen_minute_average = []

# Running lists of device temperatures in case the drivers don't have a sense
# of high or critical temperatures.
device_temperatures = {}

# Functions.
# sysload(): Function that takes a snapshot of the current system load
#   averages.  Takes no arguments.  Returns system loads as a hash table.
def sysload():
    sysload = {}
    system_load = os.getloadavg()
    sysload["one_minute"] = system_load[0]
    sysload["five_minute"] = system_load[1]
    sysload["fifteen_minute"] = system_load[2]
    return sysload

# check_sysload: Function that pulls the current system load and tests the
#   load averages to see if they're too high.  Takes seven arguments, the
#   sysload counter, the time between alerts, the value of status_polling, the
#   number of standard deviations to calculate, minimum and maximum system
#   stat queue lengths, and the name of a function to send a message with.
#   Sends a message to the user, returns an updated
#   value for sysload_counter.
def check_sysload(sysload_counter, time_between_alerts, status_polling,
    std_devs, sys_avg_min_len, sys_avg_max_len, send_message_to_user):
    message = ""
    std_dev = 0.0
    current_load_avg = sysload()

    logging.debug("Value of sys_avg_min_len: " + str(sys_avg_min_len))
    logging.debug("Value of sys_avg_max_len: " + str(sys_avg_max_len))
    logging.debug("Current system load averages: " + str(current_load_avg))

    # Copy the load averages into the appropriate running lists.
    one_minute_average.append(current_load_avg["one_minute"])
    five_minute_average.append(current_load_avg["five_minute"])
    fifteen_minute_average.append(current_load_avg["fifteen_minute"])

    logging.debug("Length of one_minute_average: " + str(len(one_minute_average)))
    logging.debug("Length of five_minute_average: " + str(len(five_minute_average)))
    logging.debug("Length of fifteen_minute_average: " + str(len(fifteen_minute_average)))

    # Pop the oldest values out of the lists to keep them at a manageable size.
    if len(one_minute_average) >= int(sys_avg_max_len):
        logging.debug("Removing oldest system load values.")
        one_minute_average.pop(0)
        five_minute_average.pop(0)
        fifteen_minute_average.pop(0)

    # To calculate the standard deviation of a group of values, there need to
    # be several available.  Make sure this is the case.
    if len(one_minute_average) < int(sys_avg_min_len):
        logging.debug("Need more than " + str(sys_avg_min_len) + " samples of system load.  Waiting.")
        return sysload_counter

    # Calculate the standard deviations of the three system loads and send an
    # alert if there's been a huge spike.
    std_dev = statistics.stdev(one_minute_average)
    logging.debug("Standard deviation of one minute system load: " + str(std_dev))
    if std_dev > float(std_devs):
        message = message + "WARNING: The current system load has spiked to " + str(current_load_avg["one_minute"]) + ".\n"

    std_dev = statistics.stdev(five_minute_average)
    logging.debug("Standard deviation of five minute system load: " + str(std_dev))
    if std_dev > float(std_devs):
        message = message + "WARNING: The five minute system load has spiked to " + str(current_load_avg["five_minute"]) + ".  What could be running that's doing this?\n"

    std_dev = statistics.stdev(fifteen_minute_average)
    logging.debug("Standard deviation of fifteen minute system load: " + str(std_dev))
    if std_dev > float(std_devs):
        message = message + "WARNING: The fifteen minute system load has spiked to " + str(current_load_avg["fifteen_minute"]) + ".  I think something's dreadfully wrong.\n"

    # If a message has been constructed, check to see if it's been longer than
    # the last time a message was sent.  If so, send it and reset the counter.
    if message:
        # If time_between_alerts is zero, alerting has been disabled so just
        # return.
        if time_between_alerts == 0:
            logging.debug("System load alerting disabled.")
            return 0
        if sysload_counter >= time_between_alerts:
            send_message_to_user(message)
            return 0

        # If enough time between alerts hasn't passed yet, just increment the
        # counter.
        sysload_counter = sysload_counter + status_polling
    return sysload_counter

# uname(): Function that calls os.uname(), extracts a few things.  This should
#   only be called upon request by the user, or maybe when the bot starts up.
#   There's no sense in having it run every time it loops.  Takes no arguments.
#   Returns a hash table containing the information.
def uname():
    system_info = {}
    sysinfo = os.uname()
    system_info["hostname"] = sysinfo[1]
    system_info["version"] = sysinfo[2]
    system_info["buildinfo"] = sysinfo[3]
    system_info["arch"] = sysinfo[4]
    return system_info

# cpus(): Takes no arguments.  Returns the number of CPUs on the system.
def cpus():
    return psutil.cpu_count()

# cpu_idle_time(): Takes no arguments.  Returns the percentage of runtime the
#   CPUs are idle as a floating point number.
def cpu_idle_time():
    return psutil.cpu_times_percent()[3]

# check_cpu_idle_time(): Monitors the amount of time the CPU(s) are idle.
#   Takes four arguments: the CPU idle time counter, the time between alerts,
#   the value of status_polling, and the name of a function to send a message
#   with.  Sends an alert to the bot's owner if the CPU idle time is too low.
#   Returns an updated value for cpu_idle_time_counter.
def check_cpu_idle_time(cpu_idle_time_counter, time_between_alerts,
        status_polling, send_message_to_user):
    message = ""
    idle_time = cpu_idle_time()

    # Check the percentage of CPU idle time and construct a message for the
    # bot's owner if it's too low.
    if idle_time < 15.0:
        message = "WARNING: The current CPU idle time is sitting at " + str(idle_time) + ".  What's keeping it so busy?"

    # If a message has been built, check to see if enough time in between
    # messages has passed.  If so, send the message.
    if message:
        # If time_between_alerts is zero, alerting has been disabled so just
        # return.
        if time_between_alerts == 0:
            logging.debug("CPU idle time alerting disabled.")
            return 0
        if cpu_idle_time_counter >= time_between_alerts:
            send_message_to_user(message)
            return 0

        # If not enough time has passed yet, just increment the counter.
        cpu_idle_time_counter = cpu_idle_time_counter + status_polling
    return cpu_idle_time_counter

# get_disk_usage(): Takes no arguments.  Returns a hash table containing the
#   disk device name as the key and percentage used as the value.
def get_disk_usage():
    disk_used = {}
    disk_partitions = None
    disk_device = None
    max = 0.0
    used = 0.0

    # Prime the hash with the names of the mounted disk partitions.
    disk_partitions = psutil.disk_partitions()
    for i in disk_partitions:
        disk_used[i.mountpoint] = ""

    # Calculate the maximum and free bytes of each disk device.
    for i in list(disk_used.keys()):
        try:
            disk_used[i] = psutil.disk_usage(i).percent
        except:
            # Docker causes this to not work with permissions problems.
            logging.debug("Skipping disk device " + i + " due to restrictive permissions.")
    return disk_used

# check_disk_usage(): Pull the amount of used storage for each disk device on
#   the system and send the bot's owner an alert if one of the disks gets too
#   full.  Takes as arguments the values of disk_usage_counter,
#   time_between_alerts, status polling, the value of disk_usage, and the name
#   of a function to send messages with.  Returns an updated value for
#   disk_usage_counter.
def check_disk_usage(disk_usage_counter, time_between_alerts, status_polling,
    disk_usage, send_message_to_user):
    message = ""
    disk_space_free = get_disk_usage()

    # Check the amount of space free on each disk device.  For each disk that's
    # running low on space construct a line of the message.
    for disk in list(disk_space_free.keys()):
        if not disk_space_free[disk]:
            logging.debug("disk_space_free[disk] isn't usable.  Forget it.")
            continue
        if disk_space_free[disk] > disk_usage:
            message = message + "WARNING: Disk device " + disk + " has " + str(100.0 - disk_space_free[disk]) + "% of its capacity left.\n"

    # If a message has been constructed, check how much time has passed since
    # the last message was sent.  If enough time has, sent the bot's owner
    # the message.
    if message:
        # If time_between_alerts is zero, alerting has been disabled so just
        # return.
        if time_between_alerts == 0:
            logging.debug("Disk usage alerting disabled.")
            return 0
        if disk_usage_counter >= time_between_alerts:
            send_message_to_user(message)
            return 0

        # Not enough time has passed.  Increment the counter and move on.
        disk_usage_counter = disk_usage_counter + status_polling
    return disk_usage_counter

# memory_utilization(): Function that returns a snapshot of memory
#    utilization.  Takes no arguments.
def memory_utilization():
    return psutil.virtual_memory()

# check_memory_utilization(): Function that checks how much memory is free on
#   the system and alerts the bot's owner if it's below a certain amount.
#   Takes five arguments, the current values of memory_free_counter and
#   time_between_alerts, the value of status_polling, the value of
#   memory_remaining, and the name of a function to send messages with.
#   Returns an updated value for memory_free_counter.
def check_memory_utilization(memory_free_counter, time_between_alerts,
        status_polling, memory_remaining, send_message_to_user):
    message = ""
    memory_stats = memory_utilization()
    calculated_free_memory = memory_stats.free + memory_stats.buffers + memory_stats.cached
    logging.debug("Calculated free memory: %s" % convert_bytes(calculated_free_memory))

    # Check the amount of memory free.  If it's below a critical threshold
    # construct a message for the bot's owner.  It's formatted this way for
    # clarity later.  Rounded off to two decimal places.
    calculated_free_memory = (calculated_free_memory / memory_stats.total)
    calculated_free_memory = round(calculated_free_memory * 100.0, 2)
    logging.debug("Percentage of free memory: %s" % str(calculated_free_memory))
    if calculated_free_memory <= memory_remaining:
        message = "WARNING: The amount of free memory has reached the critical point of " + str(calculated_free_memory) + "% free.  You'll want to see to this before the OOM killer starts reaping processes."

    # If a message has been constructed, check how much time has passed since
    # the last message was sent.  If enough time has, send the bot's owner the
    # message.
    if message:
        # If time_between_alerts is zero, alerting has been disabled so just
        # return.
        if time_between_alerts == 0:
            logging.debug("Memory utilization alerting disabled.")
            return 0
        if memory_free_counter >= time_between_alerts:
            send_message_to_user(message)
            return 0

        # Not enough time has passed.  Increment the counter and move on.
        memory_free_counter = memory_free_counter + status_polling
    return memory_free_counter

# uptime(): Function that returns the length of time the system has been
#   online from /proc/uptime.  Takes no arguments, returns a string.
def uptime():
    uptime_seconds = None
    uptime_string = None

    try:
        file = open("/proc/uptime", "r")
        uptime_seconds = float(file.readline().split()[0])
        file.close()
    except:
        return None
    uptime_string = str(timedelta(seconds = uptime_seconds))
    return uptime_string

# current_ip_address(): Function that returns the current non-RFC 1989 IP
#   address of the system using an external HTTP(S) service or REST API.
#   Takes one argument, a string containing the URL to the service.  Returns
#   the IP address as a string or None if it didn't work.
def current_ip_address(ip_addr_service):
    request = None

    # Attempt to make an HTTP(S) request to the service that returns the
    # public IP of the host.
    request = requests.get(ip_addr_service)

    # Handle catastrophic failure.
    if not request:
        logging.err("Failed to contact HTTP(S) service " + str(ip_addr_service) + " to get host's IP address.")
        return None

    # Handle HTTP error codes.
    if request.status_code != requests.codes.ok:
        logging.err("HTTP(S) request to IP address service " + str(ip_addr_service) + "failed, returned HTTP error code " + str(request.status_code) + ".")
        return None

    # Got the host's public IP address.  Explicitly cast to a string to make
    # life easier four other modules.
    logging.debug("Got current IP address of host: " + str(request.text))
    return str(request.text)

# local_ip_address(): Function that returns the local IP address of the system
#   by querying the primary network interface.  Takes no arguments.  Returns
#   the IP address as a string or None if it didn't work.
def local_ip_address():
    nics = psutil.net_if_addrs()
    primary_nic = None
    nic = None
    addr = None

    # Remove the loopback interface from the hash.  If this results in an
    # empty hash, return None.
    del nics["lo"]
    if not nics:
        logging.debug("No network interfaces found.  That's weird.")
        return None

    # Search the hash for the primary NIC.
    for nic in list(nics.keys()):
        # Make sure we filter out VPN interfaces.
        if "tun" in nic:
            continue

        for addr in nics[nic]:
            # We want AF_INET.
            if addr.family == 2:
                # Only the primary has a broadcast address.
                if addr.broadcast:
                    primary_nic = addr

    # Return the IP address if we have one, an error message if not.
    if primary_nic:
        logging.debug("Got primary IP address of system: " + primary_nic.address)
        return primary_nic.address
    else:
        logging.err("Unable to get primary IP address.  Something went wrong.")
        return "unknown.  Something went wrong"

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

# network_traffic(): Function that uses the psutil module to extract stats for
#   every network interface on the system (except for the loopback) and returns
#   them to the calling function.
def network_traffic():
    stats = {}
    nics = psutil.net_io_counters(pernic=True)

    # Get rid of the loopback interface.
    del nics["lo"]

    # Prime the network stats hash table with the remaining network interfaces.
    for i in list(nics.keys()):
        stats[i] = {}

    # For each network interface on the system, convert bytes_sent and
    # bytes_recv into human-readable strings.
    for i in list(nics.keys()):
        stats[i]["sent"] = convert_bytes(nics[i].bytes_sent)
        stats[i]["received"] = convert_bytes(nics[i].bytes_recv)
        logging.debug("Traffic volume to date for " + i + ": " + str(stats[i]))

    return stats

# centigrade_to_fahrenheit: Function that takes a floating point value
#   representing a temperature in degrees Celsius, and returns a floating
#   point value representing the temperature in degrees Fahrenheit.
def centigrade_to_fahrenheit(celsius):
    logging.debug("Entered system_stats.centigrade_to_fahrenheit().")
    logging.debug("Temperature in Centigrade: " + str(celsius))
    fahrenheit = 0.0
    fahrenheit = celsius * 9.0
    fahrenheit = celsius / 5.0
    fahrenheit = celsius + 32.0
    logging.debug("Temperature in Fahrenheit: " + str(fahrenheit))
    return fahrenheit

# get_hardware_temperatures: Function that polls the temperature monitoring
#   sensors available in the system.  Takes no arguments.  Returns a hash table
#   containing the data.  Returns None if there are no sensors (i.e., this is a
#   virtual machine).
def get_hardware_temperatures():
    return psutil.sensors_temperatures()

# check_hardware_temperatures: Function that analyzes the values of the
#   hardware temperatures and alerts the user if one of them has either reached
#   a high or critical threshold.  Takes seven arguments, the current values of
#   temperature_counter, time_between_alerts, the value of status_polling, the
#   number of standard deviations to calculate, the minimum and maximum
#   temperature stat queue lengths, and the name of a function to send
#   messages with.  Returns an updated value for temperature_counter.
def check_hardware_temperatures(temperature_counter, time_between_alerts,
    status_polling, std_devs, sys_avg_min_len, sys_avg_max_len,
    send_message_to_user):
    logging.debug("Entered function system_stats.check_hardware_temperatures().")

    message = ""
    label = ""
    temperatures = get_hardware_temperatures()
    fahrenheit = 0.0
    no_critical = False
    no_high = False
    std_dev = 0.0

    # If we're running in a virtual machine, we'll get an empty hash table.
    if not temperatures:
        logging.debug("Running on a virtual machine.  Bouncing.")
        return 0

    # If we've made it this far, we're probably running on real hardware with
    # at least one hardware sensor.
    for temp_sensor in list(temperatures.keys()):
        label = temp_sensor

        # Temperature readings take the form of lists of tuples, where the
        # tuples contain the actual data.
        for i in temperatures[temp_sensor]:
            no_high = False
            no_critical = False

            # Some sensors have internal names, some don't.  If this sensor
            # has one, replace the label with it.
            if i[0]:
                label = i[0]
            logging.debug("Name of sensor: " + label)

            # Schema of tuples:
            #   0: Internal label (can be blank)
            #   1: Current temperature (in Centigrade)
            #   2: Temperature the driver considers too high (can be None)
            #   3: Temperature the driver considers dangerously high (can be
            #       None)
            # Check to see if the critical point is set and has been reached.
            if i[3]:
                if i[1] >= i[3]:
                    if time_between_alerts == 0:
                        logging.debug("System temperature alerting disabled.")
                        continue
                    fahrenheit = centigrade_to_fahrenheit(i[1])
                    message = "WARNING: Temperature sensor " + label + " is now reading " + str(i[1]) + " degrees Centigrade (" + str(fahrenheit) + " degrees Fahrenheit).  This is alarmingly high!"
                    send_message_to_user(message)
                    continue
            else:
                no_critical = True
                logging.debug("Sensor " + label + " does not have a critical point defined.")

            # Check to see if the too high point is set and has been reached.
            # We only want one of these.
            if i[2]:
                if i[1] >= i[2]:
                    # If time_between_alerts is zero, alerting has been
                    # disabled so just move on.
                    if time_between_alerts == 0:
                        logging.debug("System temperature alerting disabled.")
                        continue

                    fahrenheit = centigrade_to_fahrenheit(i[1])
                    message = "DANGER: Temperature sensor " + label + " is now reading " + str(i[1]) + " degrees Centigrade (" + str(fahrenheit) + " degrees Fahrenheit).  Critical temperature reached!  Investigate immediately!"
                    send_message_to_user(message)
                    continue
            else:
                no_high = True
                logging.debug("Sensor " + label + " does not have a high point defined.")

            # If there are no high or critical points defined by the driver, we
            # have to fall back on a statistical analysis of temperature
            # history.
            if no_high or no_critical:
                std_dev = 0.0

                # If a list of device temperatures for this device doesn't
                # exist, add it to the hash.
                if label not in list(device_temperatures.keys()):
                    logging.debug("Creating temperature history for device " + label + ".")
                    device_temperatures[label] = []

                # Make sure the temperature makes sense.
                if i[1] <= 0.0:
                    logging.debug("Temperature for device " + label + " is negative.  This makes no sense.  Skipping.")
                    continue

                # Store the current temperature in Centigrade.
                device_temperatures[label].append(i[1])
                logging.debug("Length of device_temperatures[" + label + "]: " + str(len(device_temperatures[label])))

                # Pop the oldest values out of the list to keep it at a
                # manageable size.
                if len(device_temperatures[label]) >= int(sys_avg_max_len):
                    logging.debug("Removing oldest temperature for device_temperatures[" + label + "]."  )
                    device_temperatures[label].pop(0)

                # To calculate the standard deviation of a group of values,
                # there need to be several available.  Make sure this is the
                # case.
                if len(device_temperatures[label]) < int(sys_avg_min_len):
                    logging.debug("Need more than " + str(sys_avg_min_len) + " temperature samples.  Waiting.")
                    continue

                # Calculate the standard deviations of the three system loads
                # and send an alert if there's been a spike.
                std_dev = statistics.stdev(device_temperatures[label])
                logging.debug("Standard deviation of temperature of sensor " + label + ": " + str(std_dev))
                if std_dev > float(std_devs):
                    # If time_between_alerts is zero, alerting has been
                    # disabled so just move on.
                    if time_between_alerts == 0:
                        logging.debug("System temperature alerting disabled.")
                        continue

                    fahrenheit = centigrade_to_fahrenheit(i[1])
                    message = message + "WARNING: The temperature of sensor " + label + " has spiked to " + str(i[1]) + " degrees Centigrade (" + str(fahrenheit) + " degrees Fahrenheit)!  Investigate immediately!"
            # Bottom of cycle through sensors on this device.
        # Bottom of cycle through temperature sensors on the system.

    # If a message has been sent in the recent past, check to see if it's been
    # longer than the last time a message was sent.  If so, reset the counter.
    if message:
        if temperature_counter >= time_between_alerts:
            send_message_to_user(message)
            logging.debug("Resetting time between alerts counter to 0.")
            return 0

        # If enough time between alerts hasn't passed yet, just increment the
        # counter.
        temperature_counter = temperature_counter + status_polling
        logging.debug("Incrementing time between alerts counter.")
    return temperature_counter

if "__name__" == "__main__":
    pass
