#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# processes.py - Module that implements the system-process related stuff for
#   system_bot.py.

# By: The Doctor <drwho at virtadpt dot net>
#       0x807B17C1 / 7960 1CDC 85C9 0B63 8D9F  DD89 3BD8 FF2B 807B 17C1

# License: GPLv3

# v2.1 - Added the ability to find out the top X running processes on the
#        system.
# v2.0 - Ported to Python 3.
# v1.0 - Initial release.

# TO-DO:
# - Rewrite processes.get_process_list() to use psutil instead.

# Load modules.
import logging
import os
import psutil
import subprocess
import sys

# Functions.
# get_process_list(): Function that pulls a list of processes running on the
#   local system as a large string.
def get_process_list():
    return os.popen("ps ax").read()

# check_process_list(): Function that walks through a list of things to look
#   for in the system's process table and builds another list of things that
#   need to be restarted.  Takes one argument, a list of processes.  Returns
#   an empty list if everything is fine, "error" if the value of 'processes'
#   isn't defined, or another list of processes that need to be restarted.
def check_process_list(processes):
    logging.debug("Processes to look for: " + str(processes))

    crashed_processes = []

    # Check the list of monitored processes.
    process_list = get_process_list()
    for process in processes:
        if process[0] not in process_list:
            crashed_processes.append(process)
    logging.debug("Dead processes : " + str(crashed_processes))
    return crashed_processes

# restart_crashed_processes(): Function that walks through a list of crashed
#   processes and restarts them, one by one to ensure they start back up.  The
#   function then tests to ensure that the processes are back in the process
#   table.  The function will attempt to restart the processes a configurable
#   number of times, defaulting to five.  Takes two arguments, a list of
#   strings which constitute full command lines to restart the processes and
#   the number of times to try to restart them.  Returns True if it worked, or
#   False if it didn't.
def restart_crashed_processes(processes, retries=5):
    logging.debug("Processes to restart: " + str(processes))

    crashed_processes = []
    command = None
    pid = None

    # Walk the list of processes to restart and try to bring them back up.
    for process in processes:
        for i in range(0, retries):
            command = process[1].split()

            # Make the first element of the command a full path to the
            # executable before caling it.
            logging.debug("Restarting dead process: " + process[0])
            command[0] = sys.executable
            pid = subprocess.Popen(command)

            # Check the process list to make sure it came back up.
            if not check_process_list(process):
                logging.debug("Success!  Restarted process " + process[0] + "!")
                break
        else:
            logging.debug("Unable to restart crashed process: " + process[0])
            crashed_processes.append(process)

    logging.debug("Dead processes : " + str(crashed_processes))
    return crashed_processes

# def get_top_processes(): Function that uses psutil to figure out what the
#   busiest processes on the system are.  Use case: "What the hell is burning
#   all the CPU time?"  Takes one optional argument, the number of top-X
#   processes to find.  Defaults to 5.  Returns a list of lists of the top X
#   processes, in descending order of CPU percentage taken up.
# MOOF: I'm leaving the function argument as-is because eventually I'd like
#   to make this more interactive based upon user input.  But that's going to
#   require a more solid understanding of the base case.
def get_top_processes(number_of_processes=5):
    top_processes = []
    process = None

    # Built an array of the processes running on the server.
    for process in psutil.process_iter():
        process_info = process.as_dict(attrs=["cmdline", "name", "cpu_percent",
            "pid"])

        # Kernel threads have empty cmdline values.  Skip them.
        if not process_info["cmdline"]:
                continue

        # Due to the fact that we want actually awake processes, skip running
        # processes that have CPU utilization of 0.0.
        if not process_info["cpu_percent"]:
                continue
        top_processes.append(process_info)

    # Catch the case where the process list is empty due to the above CPU
    # percentage case.
    if len(top_processes) == 0:
        return None

    # Sort the array based upon CPU time utilized.
    top_processes = sorted(top_processes, key=lambda process:
        process["cpu_percent"], reverse=True)

    # Return the top X processes on the system.
    top_processes = top_processes[0:number_of_processes+1]
    logging.debug("Top processes on the system: " + str(top_processes))
    return(top_processes)

if __name__ == "__main__":
    print("List of system processes:")
    print(get_process_list())

    print("Processes that should always be running:")
    print(check_process_list(["jfsCommit", "jfsSync"]))

    print("Processes that should never be running:")
    print(check_process_list(["nomatch", "this should never match"]))
    sys.exit(0)

