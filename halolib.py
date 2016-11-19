#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# This is a module which collects all of the common functions and methods in
# the Exocortex Halo into one place.  This'll make future maintenance and
# adding new bots later somewhat easier.

# By: The Doctor <drwho at virtadpt dot net>
#     0x807B17C1 / 7960 1CDC 85C9 0B63 8D9F  DD89 3BD8 FF2B 807B 17C1

# License: GPLv2
# Pre-requisite modules have their own licenses.

# v1.0 - Initial release.

# TO-DO:

# Load modules.
import sys

# Constants.

# Global variables.

# If this is a class or module, say what it is and what it does.

# Classes.

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

# Core code...
if __name__ == '__main__':
    # Unit tests go here...
    sys.exit(0)

# Fin.

