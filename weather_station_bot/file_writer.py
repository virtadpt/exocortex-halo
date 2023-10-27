#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# file_writer.py - A Weather Bot module that writes the values it's given to
#   a file on disk on a schedule.
#
#   This is part of the Exocortex Halo project
#   (https://github.com/virtadpt/exocortex-halo/).

# v1.1 - Changed the file format to a more explicit key=value format by adding
#        an equals sign (=) to the output.
# v1.0 - Initial release.

# TODO:
# -

# By: The Doctor <drwho at virtadpt dot net>
#     0x807B17C1 / 7960 1CDC 85C9 0B63 8D9F  DD89 3BD8 FF2B 807B 17C1

# License: GPLv3

import logging
import os
import sys

# write_values_to_file():  Given a file path, write the key-value pairs (passed
#   as keyword arguments) to the file.
def write_values_to_file(output_file, **kwargs):
    logging.debug("Entered file_writer.write_values_to_file().")

    output_path = ""
    writer = None

    # Normalize the full path to the output file.
    output_file = os.path.abspath(output_file)
    logging.debug("Normalized output file path: %s" % output_file)

    # Extract the path to the output file.
    output_path = os.path.dirname(output_file)
    logging.debug("Output path: %s" % output_path)

    # If the file exists already, delete it.
    if os.path.exists(output_file):
        try:
            os.remove(output_file)
        except:
            logging.error("Unable to delete output file %s." % output_file)

    # If the directory spec doesn't exist, create it.  Return False if we
    # can't.
    if not os.path.isdir(output_path):
        try:
            os.makedirs(output_path)
            logging.info("Created output directory %s" % output_path)
        except:
            logging.error("Unable to create output directory %s" % output_path)
            return(False)

    writer = open(output_file, "w")
    try:
        # Write the kwargs out to the file in key-value format, one line at
        # a time.  If it fails, return False.
        for key in kwargs.keys():
            writer.write("%s=%s\n" % (key, kwargs[key]))

    except:
        logging.error("Unable to write to file %s!" % output_file)
        return(False)
        
    finally:
        logging.info("Successfully wrote to file %s." % output_file)
        writer.close()

    return(True)

# Core code.
if __name__ == "__main__":
    # Configure the logger.  DEBUG for interactive testing.
    logging.basicConfig(level=10, format="%(levelname)s: %(message)s")
    logger = logging.getLogger(__name__)

    print("Initiating self test.")
    write_values_to_file("/tmp/test_output.txt", foo=1, bar=2, baz=3)
    sys.exit(0)

