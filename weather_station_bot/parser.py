#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# parser.py - Module for weather_station_bot.py that implements all of the
#   parsing related functions.

# By: The Doctor <drwho at virtadpt dot net>
#       0x807B17C1 / 7960 1CDC 85C9 0B63 8D9F  DD89 3BD8 FF2B 807B 17C1

# License: GPLv3

# v1.0 - Initial release.

# TO-DO:
# - Maybe make the parsing elements more composable, like they are for System
#   Bot?
# - 

# Load modules.
import logging
import pyparsing as pp
import sys

# Parser primitives.
# We define them up here because they'll be re-used over and over.
help_command = pp.CaselessLiteral("help")

wind_speed_command = pp.CaselessLiteral("wind speed")

wind_direction_command = pp.CaselessLiteral("wind direction")
direction_command = pp.CaselessLiteral("direction")
wind = pp.Or([wind_direction_command, direction_command])

temperature_command = pp.CaselessLiteral("temperature")
temp_command = pp.CaselessLiteral("temp")
temperature = pp.Or([temperature_command, temp_command])

air_pressure_command = pp.CaselessLiteral("air pressure")
atmospheric_pressure_command = pp.CaselessLiteral("atmospheric pressure")
barometric_pressure_command = pp.CaselessLiteral("barometric pressure")
pressure_command = pp.CaselessLiteral("pressure")
air_pressure = pp.Or([air_pressure_command, atmospheric_pressure_command,
    barometric_pressure_command, pressure_command])

relative_humidity_command = pp.CaselessLiteral("relative humidity")
air_humidity_command = pp.CaselessLiteral("air humidity")
humidity_command = pp.CaselessLiteral("humidity")
humidity = pp.Or([relative_humidity_command, air_humidity_command,
    humidity_command])

rain_gauge_command = pp.CaselessLiteral("rain gauge")
raining_command = pp.CaselessLiteral("raining")
is_it_raining_command = pp.CaselessLiteral("is it raining")
rain = pp.Or([rain_gauge_command, raining_command, is_it_raining_command])

# parse_help(): Function that matches the word "help" all by itself in an input
#   string.  Returns the string "help" on a match and None if not.
def parse_help(command):
    try:
        parsed_command = help_command.parseString(command)
        return "help"
    except:
        return None

# parse_wind_speed(): Function that matches the string "wind speed" all by
#   itself an input string.  Returns the string "speed" on a match and None
#   if not.
def parse_wind_speed(command):
    try:
        parsed_command = wind_speed_command.parseString(command)
        return "speed"
    except:
        return None

# parse_wind_direction(): Function that matches the strings "wind direction" or
#   "direction" all by themselves in an input string.  Returns the string
#   "direction" on a match and None if not.
def parse_wind_direction(command):
    try:
        parsed_command = wind.parseString(command)
        return "direction"
    except:
        return None

# parse_temperature(): Function that matches the strings "temperature" or
#   "temp" all by themselves in an input string.  Returns the string "temp" on
#   a match and None if not.
def parse_temperature(command):
    try:
        parsed_command = temperature.parseString(command)
        return "temp"
    except:
        return None

# parse_pressure(): Function that matches the strings "air pressure",
#   "atmospheric pressure", or "pressure" all by themselves in an input string.
#   Returns the string "pressure" on a match and None if not.
def parse_pressure(command):
    try:
        parsed_command = air_pressure.parseString(command)
        return "pressure"
    except:
        return None

# parse_humidity(): Function that matches the strings "relative humidity",
#   "air humidity", or "humidity" all by themselves in an input string.
#   Returns the string "humidity" on a match and None if not.
def parse_humidity(command):
    try:
        parsed_command = humidity.parseString(command)
        return "humidity"
    except:
        return None

# parse_rain(): Function that matches one of the strings "rain gauge",
#   "raining", or "is it raining" in an input string.  Returns the string
#   "rain" on a match and None if not.
def parse_rain(command):
    try:
        parsed_command = rain.parseString(command)
        return "rain"
    except:
        return None

# parse_command(): Function that parses commands from the message bus.
#   Commands come as strings and are run through PyParsing to figure out what
#   they are.  A single-word string is returned as a match or None on no match.
#   Conditionals are short-circuited to speed up execution.
def parse_command(command):
    parsed_command = None

    # Clean up the incoming command.
    command = command.strip()
    command = command.strip('.')
    command = command.strip(',')
    command = command.lower()

    # If the get request is empty (i.e., nothing in the queue), bounce.
    if "no commands" in command:
        return None

    # Online help?
    parsed_command = parse_help(command)
    if parsed_command == "help":
        return parsed_command

    # Wind speed?
    parsed_command = parse_wind_speed(command)
    if parsed_command == "speed":
        return parsed_command

    # Wind direction?
    parsed_command = parse_wind_direction(command)
    if parsed_command == "direction":
        return parsed_command

    # Temperature?
    parsed_command = parse_temperature(command)
    if parsed_command == "temp":
        return parsed_command

    # Air pressure?
    parsed_command = parse_pressure(command)
    if parsed_command == "pressure":
        return parsed_command

    # Humidity?
    parsed_command = parse_humidity(command)
    if parsed_command == "humidity":
        return parsed_command

    # Rain?
    parsed_command = parse_rain(command)
    if parsed_command == "rain":
        return parsed_command

    # Fall-through: Nothing matched.
    return "unknown"

if __name__ == "__main__":
    print("Things the parser knows to look for:")
    print(" * help")
    print(" * wind speed")
    print(" * wind direction")
    print(" * direction")
    print(" * temperature")
    print(" * temp")
    print(" * air pressure")
    print(" * atmospheric pressure")
    print(" * barometric pressure")
    print(" * pressure")
    print(" * air humidity")
    print(" * relative humidity")
    print(" * humidity")
    print(" * rain gauge")
    print(" * raining")
    print(" * is it raining")
    sys.exit(0)

