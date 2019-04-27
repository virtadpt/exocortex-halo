#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# exocortex_sip_client.py - Registers itself with a SIP provider (like voip.ms)
#   as a client so that VoIP calls can be placed.  This application takes an
#   audio file of some kind, starts a SIP session, and plays the audio through
#   the connection.

# By:  The Doctor [412/724/301/703/415/510] <drwho at virtadpt dot net>

# License: GPLv3

# v3.0 - Ported to Python 3.
#         - Reworked status and debugging output while I debugged the bot.
#           Reworked some comments, too, while I re-familiarized myself with
#           the bot's code.
#         - Made the playback delay settable on the command line.
# v2.0 - I've reworked so much stuff, this is effectively a new version.
# v1.2 - Updated to take into account the latest version of pjsip (v2.7.2).
#      - Reworked the code a little, in part to refamiliarize myself with it
#        and in part to make it match the rest of my code more closely, because
#        I have more experience under my belt now.
#      - Reworked some comments.
#      - Reworked this bot so it uses a config file instead of having to edit
#        the code to configure it (what was I thinking?!)
# v1.1 - Added handlers for SIP response codes 30x.
#      - Fixed off-by-one errors in SIP response parsers.
#      - Changed playback delay to 5 seconds, because why not, VoIP is hard.
#      - Updated comments here and there.  Nothing to write home about.
#      - Changed the speech playback code so that it time.sleep()'s for
#        ((duration of .wav) + 1) * 2 for a sick, stupid reason that required an
#        ugly hack.  When testing this code in the field I spent most of a day
#        figuring out why PJSIP kept killing itself prematurely.  As it turns
#        out, where the code places the call and goes to sleep to wait for the
#        .wav to finish playing, it was waiting only as long as the .wav file
#        would play and then terminating itself normally, after that many
#        seconds.  What wasn't obvious was the way PJSIP uses callbacks and
#        their associated threads which the global timer starts running the
#        moment the call attempt begins, not when the other end picks up.  So
#        I doubled the amount of time the core code time.sleep()'s and it
#        magickally started to work.  I fully admit this is a truly ugly hack
#        that only Helen Keller could love on payday but it made everything
#        work after a frustrating day.  I mostly wrote this lengthy and
#        unnecessary changelog entry in the hope that Google, et al index this
#        text and save other users of PJSIP twelve hours of cursing, scratching
#        their heads, and drinking way too much coffee.  The text PJSIP barfs
#        up right before it kills itself is:
#
# python2: ../src/pjsua-lib/pjsua_acc.c:586: pjsua_acc_get_user_data: Assertion `pjsua_var.acc[acc_id].valid' failed.
# Aborted (core dumped)
#
#   I didn't want to do something less weird like hardcode a delay between the
#   start of the call attempt and the confirmation of the call attempt because
#   you can't make those kinds of assumptions.  Network weather patterns differ
#   from moment to moment, servers at different VoIP providers are different,
#   and the system load of the underlying VPS you might be running this on
#   changes.  And that's just spitballing reasons.  So, make the delay long and
#   let the other end hang up on their own.
# v1.0 - Initial release.

# TO-DO:
# - Figure out how to place calls to SIP addresses as well as phone numbers.

# Load modules.
import argparse
import configparser
import contextlib
import logging
import os
import pjsua
import sys
import threading
import time
import wave

# Global variables.
# Handles for the CLI argument parser handler.
argparser = None
args = None

# Handle to a configuration file parser.
config = None

# User credentials for the Exocortex SIP account.
sip_username = ""
sip_registrar = ""
sip_password = ""

# How long to wait before telling the media processor to start playback.
# Delay is in seconds.
delay = 5

# Handles for the PJSUA objects that need to be instantiated.
lib = None
account = None

# Global handle for the current SIP call.
current_call = None

# Phone number to call.
call_destination = ""

# Handles for the media engine and the .wav player.
wav_player = ""
wav_player_slot = 0

# File specifics on the .wav file to play back.
wav_frames = 0
wav_rate = 0
wav_duration = 0.0

# Classes.
# MyAccountCallback(): Callback class for Account objects.  Receives and
#   handles status events, mostly.  Necessary for anything involving SIP
#   account objects.
class MyAccountCallback(pjsua.AccountCallback):
    # Because this is a threaded class, we need to allocate at least one
    # semaphore to take care of it.
    semaphore = None

    # Initialize instances of this object.  By default, use the __init__() of
    # the underlying class.  An instance of the pjsua.Account class is passed
    # to this method.
    def __init__(self, account):
        pjsua.AccountCallback.__init__(self, account)

    # Kicks the thread off by either grabbing or waiting to grab the PJSUA
    # library's thread semaphore.
    def wait(self):
        logger.debug("Trying to grab MyAccountCallback.semaphor...")
        self.semaphore = threading.Semaphore(0)
        self.semaphore.acquire()
        logger.debug("...got it.")

    # Method that reacts to changes in the state of SIP registration.
    def on_reg_state(self):
        if self.semaphore:
            # If we are successfully registered with the SIP provider, release
            # the semaphore.
            if self.account.info().reg_status >= 200 and self.account.info().reg_status < 300:
                self.semaphore.release()

            # Detect redirection responses.
            if self.account.info().reg_status >= 300 and self.account.info().reg_status < 400:
                logger.error("Server sent a redirection response: " + str(self.account.info().reg_reason))

            # Detect client failures, i.e., problems or mistakes on our end.
            if self.account.info().reg_status >= 400 and self.account.info().reg_status < 500:
                logger.error("Client registration error: " + str(self.account.info().reg_reason))

            # Detect server failures, i.e., problems not on our end.
            if self.account.info().reg_status >= 500 and self.account.info().reg_status < 600:
                logger.error("Server communication or registration error: " + str(self.account.info().reg_reason))

            # Detect all other kinds of failures.
            if self.account.info().reg_status >= 600:
                logger.fatal("Holy shit, what did you do?!?! " + str(self.account.info().reg_reason))

# MyCallCallback(): Callback class that receives and handles SIP call events.
class MyCallCallback(pjsua.CallCallback):

    # Initialize instances of this object.  By default, use the __init__() of
    # the underlying class.  An instance of the pjsua.Call class is passed
    # to this method, which corresponds to an active call attempt.
    def __init__(self, call=None):
        pjsua.CallCallback.__init__(self, call)

    # Method that handles call state changes.
    def on_state(self):
        # Reference current_call in the global context.
        global current_call

        # Display status update.
        logger.info("Call with" + str(self.call.info().remote_uri))
        logger.info("is" + str(self.call.info().state_text))
        logger.info("last status code ==" + str(self.call.info().last_code))

        # Detect disconnection events for SIP calls.
        if self.call.info().state == pjsua.CallState.DISCONNECTED:
            current_call = None
            logger.info("SIP call has been disconnected.")

    # Method that implements state changes in the media processor.
    def on_media_state(self):
        if self.call.info().media_state == pjsua.MediaState.ACTIVE:
            # Capture the call_slot for the currently active call.
            call_slot = self.call.info().conf_slot

            # Sleep for a little while to give the callee a chance to pick
            # up the phone.
            time.sleep(float(delay))

            # Connect the media player to the call and vice versa.
            pjsua.Lib.instance().conf_connect(wav_player_slot, call_slot)
            pjsua.Lib.instance().conf_connect(call_slot, wav_player_slot)
            logger.info("Media processor is now active.")
        else:
            logger.info("Media processor is now inactive.")

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
# Set up the command line argument parser.
argparser = argparse.ArgumentParser(description="A command line utility which initiates a SIP session with a VoIP service, places a phone call, and plays an arbitrary .wav file into the connection.")
argparser.add_argument("--production", action="store_true",
    help="Don't try to initialize a sound device when won't exist anyway.")
argparser.add_argument("--phone-number", action="store", default="2064560649",
    help="Specify a phone number to call (no dashes, e.g., 2125551212).")
argparser.add_argument("--message", action="store",
    help="Full path to a .wav file to play back into the call.  Required.")
argparser.add_argument("--username", action="store", default="UNKNOWN",
    help="Optional username to add to outbound SIP packets.")
argparser.add_argument("--config", action="store",
    default="./exocortex_sip_client.conf",
    help="Full path to a configuration file.")
argparser.add_argument('--loglevel', action='store',
    help='Valid log levels: critical, error, warning, info, debug, notset.  Defaults to INFO.')
argparser.add_argument("--delay", action="store",
    help="Delay in seconds between initiating a SIP call and starting to play the audio file.  Defaults to five (5) seconds.  I strongly suggest figuring out a value that works reliably for you and setting it in the config file.")

# Parse the command line args, if any.
args = argparser.parse_args()
if args.production:
    print("Production mode enabled.  No sound hardware enabled.")

# If no number to call was given, ABEND because we can't place a call.
if not args.phone_number:
    print("No phone number given - can't call anyone!")
    sys.exit(1)

# Ensure that there is a media file of some kind to play into the call.
if not args.message:
    print("ERROR: You must specify a path to a .wav file to play into your call.")
    sys.exit(1)
else:
    # Make sure the file exists.  ABEND if not.
    if not os.path.exists(args.message):
        print("ERROR: The .wav file with the message doesn't exist.  Did you get the path right?")
        sys.exit(1)

# If a configuration file has been specified on the command line, parse it.
config = configparser.ConfigParser()
if not os.path.exists(args.config):
    print("Unable to find or open configuration file " + args.config + ".")
    sys.exit(1)
config.read(args.config)

# Get the SIP credentials from the config file.
sip_username = config.get ("DEFAULT", "sip_username")
sip_registrar = config.get ("DEFAULT", "sip_registrar")
sip_password = config.get ("DEFAULT", "sip_password")

# Get the delay (in seconds) before starting playback.
delay = config.get ("DEFAULT", "delay")

# Get the default loglevel of the bot.
config_log = config.get("DEFAULT", "loglevel").lower()
if config_log:
    loglevel = set_loglevel(config_log)

# Set the delay on the command line, overriding the config file if it exists.
if args.delay:
    delay = int(args.delay)

# Set the loglevel from the override on the command line if it exists.
if args.loglevel:
    loglevel = set_loglevel(args.loglevel.lower())

# Configure the logger.
logging.basicConfig(level=loglevel, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Debugging output, if required.
logger.info("Everything is configured.")
logger.debug("Values of configuration variables as of right now:")
logger.debug("Production mode: " + str(args.production))
logger.debug("Phone number to call: " + str(args.phone_number))
logger.debug("Audio file to play: " + str(args.message))
logger.debug("Outbound username: " + str(args.username))
logger.debug("Configuration file: " + str(args.config))
logger.debug("SIP username: " + str(sip_username))
logger.debug("SIP registrar: " + str(sip_registrar))
logger.debug("SIP password: " + str(sip_password))
logger.debug("Delay (in seconds): " + str(delay))

# Allocate an instance of the PJSUA library interface.
lib = pjsua.Lib()

# Try to initialize the PJSUA library interface, set a transport, and start
# the engine up.
try:
    lib.init()
    lib.create_transport(pjsua.TransportType.UDP)
    lib.start()

    # In production mode (read: running on a VPS) disable the default sound
    # device because there won't be one, anyway.
    if args.production:
        lib.set_null_snd_dev()

    # Register with the SIP provider.
    account = lib.create_account(pjsua.AccountConfig(sip_registrar,
        sip_username, sip_password, args.username))

    # Attach a callback to the account object so we can keep track of the
    # call status.
    account_callback = MyAccountCallback(account)
    account.set_callback(account_callback)

    # Start the account callback object so it'll receive events.
    account_callback.wait()

    # Display registration status.
    logger.info("SIP registration complete, status: " + str(account.info().reg_status))

    # Create a SIP URI for the destination to call.
    call_destination = "sip:" + args.phone_number + "@" + sip_registrar

    # Allocate a .wav playback object.
    wav_player = lib.create_player(args.message)
    wav_player_slot = lib.player_get_slot(wav_player)

    # Try to place a call to the generated SIP URI.
    logger.info("Placing call to " + call_destination + "...")
    try:
        account.make_call(call_destination, cb=MyCallCallback())
    except pjsua.Error as call_error:
        logger.error("ERROR: Unable to place call: " + str(call_error))

    # Calculate the duration of the .wav file to play into the call.
    with contextlib.closing(wave.open(args.message, 'r')) as wav_file:
        wav_frames = wav_file.getnframes()
        wav_rate = wav_file.getframerate()
        wav_duration = wav_frames / float(wav_rate)

        # Oh gods, this is an ugly hack.
        wav_duration = (int(round(wav_duration)) + 1) * 2
        logger.debug("Duration of audio message: " + str(wav_duration) + " seconds")

    # Wait for the .wav file to finish.
    logger.info("Waiting for audio message to finish playing...")
    time.sleep(wav_duration)

except pjsua.Error as err:
    logger.error("ERROR: Unable to initalize PJSUA interface: " + str(err))

# Tear down the library interface objects.
logger.debug("Terminating session with SIP registrar.")
account.delete()
account = None

logger.debug("Deallocating internal VoIP engine.")
lib.destroy()
lib = None

# Fin.
logger.info("Done.  Exiting.")
sys.exit(0)
