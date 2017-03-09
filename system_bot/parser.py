#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# parser.py - Module for system_bot.py that implements all of the parsing
#   related functions.

# By: The Doctor <drwho at virtadpt dot net>
#       0x807B17C1 / 7960 1CDC 85C9 0B63 8D9F  DD89 3BD8 FF2B 807B 17C1

# License: GPLv3

# v2.0 - Split all the code up into separate modules.
# v1.0 - Initial release.

# TO-DO:
# - 

# Load modules.
import pyparsing as pp

# Parser primitives.
# We define them up here because they'll be re-used over and over.
help_command = pp.CaselessLiteral("help")
load_command = pp.CaselessLiteral("load")
sysload_command = pp.CaselessLiteral("sysload")
system_load_command = pp.CaselessLiteral("system load")
load_or_system_load_command = pp.Or([load_command, sysload_command,
    system_load_command])
uname_command = pp.CaselessLiteral("uname")
info_command = pp.CaselessLiteral("info")
system_info = pp.CaselessLiteral("system info")
system_info_command = pp.Or([uname_command, info_command, system_info])
cpus_command = pp.CaselessLiteral("cpus")
disk_command = pp.CaselessLiteral("disk")
disk_usage_command = pp.CaselessLiteral("disk usage")
storage_command = pp.CaselessLiteral("storage")
free_disk_space_command = pp.Or([disk_command, disk_usage_command,
    storage_command])
memory_command = pp.CaselessLiteral("memory")
free_memory_command = pp.CaselessLiteral("free memory")
ram_command = pp.CaselessLiteral("ram")
free_ram_command = pp.CaselessLiteral("free ram")
unused_memory_command = pp.Or([memory_command, free_memory_command, ram_command,
    free_ram_command])

# parse_help(): Function that matches the word "help" all by itself in an input
#   string.  Returns the string "help" on a match and None if not.
def parse_help(command):
    try:
        parsed_command = help_command.parseString(command)
        return "help"
    except:
        return None

# parse_system_load(): Function that matches the strings "load" or "system load"
#   all by themselves in an input string.  Returns the string "load" on a match
#   and None if not.
def parse_system_load(command):
    try:
        parsed_command = load_or_system_load_command.parseString(command)
        return "load"
    except:
        return None

# parse_system_info(): Function that matches the strings "uname" or "system
#   info" or "info" all by themselves in an input string.  Returns the string
#   "info" on a match and None if not.
def parse_system_info(command):
    try:
        parsed_command = system_info_command.parseString(command)
        return "info"
    except:
        return None

# parse_cpus(): Function that matches the strings "cpus" or "CPUs" all by
#   themselves in an input string.  Returns the string "cpus" on a match and
#   None if not.
def parse_cpus(command):
    try:
        parsed_command = cpus_command.parseString(command)
        return "cpus"
    except:
        return None

# parse_disk_space(): Function that matches the strings "disk", "disk usage",
#   or "storage" all by themselves in an input string.  Returns the string
#   "disk" on a match and None if not.
def parse_disk_space(command):
    try:
        parsed_command = free_disk_space_command.parseString(command)
        return "disk"
    except:
        return None

# parse_free_memory(): Function that matches the strings "memory", "free
#   memory", "ram", or "free ram" all by themselves in an input string.
#   Returns the string "memory" on a match and None if not.
def parse_free_memory(command):
    try:
        parsed_command = unused_memory_command.parseString(command)
        return "memory"
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

    # System load?
    parsed_command = parse_system_load(command)
    if parsed_command == "load":
        return parsed_command

    # System info?
    parsed_command = parse_system_info(command)
    if parsed_command == "info":
        return parsed_command

    # CPUs?
    parsed_command = parse_cpus(command)
    if parsed_command == "cpus":
        return parsed_command

    # Free disk space?
    parsed_command = parse_disk_space(command)
    if parsed_command == "disk":
        return parsed_command

    # Free memory?
    parsed_command = parse_free_memory(command)
    if parsed_command == "memory":
        return parsed_command

    # Fall-through: Nothing matched.
    return "unknown"

if "__name__" == "__main__":
    pass

