#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# test_sip_client.py - Registers itself with a SIP provider (like voip.ms)
#   as a SIP client so that VoIP calls can be placed with it.  This application
#   takes arbitrary text through an interface of some kind that I haven't
#   figured out yet, runs it through a text-to-speech application, and then
#   places a SIP call.

# By:  The Doctor [412/724/301/703/415][ZS] <drwho at virtadpt dot net>

# License: GPLv3

# v1.0 - Initial release.

# TO-DO:

# Load modules.
import argparse
import contextlib
import os
import pjsua
import sys
import threading
import time
import wave

# Constants.
# User credentials for the Exocortex SIP account.
USERNAME = '<SIP provider username>'
HOST = '<SIP registrar>'
PASSWORD = '<SIP provider password>'

# How long to wait before telling the media processor to start playback.
# Delay is in seconds.
DELAY_BEFORE_PLAYBACK = 4

# Global variables.
# Handles for the PJSUA objects that need to be instantiated.
lib = ''
account = ''

# Global handle for the current SIP call.
current_call = ''

# Phone number of the call's destination and SIP URI to call.
phone_number = ''
call_destination = ''

# Handle to a CLI argument parser handler.
argparser = ''
args = ''

# Holds the path of a .wav file to play back into the call.
outbound_message = ''

# Flag that specifies whether or not it's being run on an Exocortex server.
production_mode = False

# Handles for the media engine and the .wav player.
wav_player = ''
wav_player_slot = 0

# Outbound username to spoof.
outbound_username = ''

# File specifics on the .wav file to play back.
wav_frames = 0
wav_rate = 0
wav_duration = 0.0

# Classes.
# MyAccountCallback(pjsua.AccountCallback): Callback class for Account objects.
#   Receives and handles status events, mostly.  Necessary for anything
#   involving SIP account objects.
class MyAccountCallback(pjsua.AccountCallback):
    # Because this is a threaded class, we need to allocate at least one
    # semaphore to take care of it.
    semaphore = None

    # Initialize instances of this object.  By default, use the __init__() of
    # the underlying class.  An instance of the pjsua.Account class is passed
    # to this method.
    def __init__(self, account):
        pjsua.AccountCallback.__init__(self, account)

    # Kicks the method/thread off by either grabbing or waiting to grab the
    # PJSUA library's thread semaphore.
    def wait(self):
        self.semaphore = threading.Semaphore(0)
        self.semaphore.acquire()

    # Method that reacts to changes in the state of SIP registration.
    def on_reg_state(self):
        if self.semaphore:
            # If we are successfully registered with the SIP provider, release
            # the semaphore.
            if self.account.info().reg_status >= 200:
                self.semaphore.release()

            # Detect client failures, i.e., problems or mistakes on our end.
            if self.account.info().reg_status >= 400 and self.account.info().reg_status <= 500:
                print "ERROR: Client registration error: ",
                print self.account.info().reg_reason

            # Detect server failures, i.e., problems not on our end.
            if self.account.info().reg_status >= 500 and self.account.info().reg_status <= 600:
                print "ERROR: Server communication or registration error: ",
                print self.account.info().reg_reason

            # Detect all other kinds of failures.
            if self.account.info().reg_status >= 600:
                print "ERROR: Holy shit, what did you do?!?! "
                print self.account.info().reg_reason

# MyCallCallback(pjsua.CallCallback): Callback class that receives and handles
#   events related to SIP calls.
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
        print "Call with", self.call.info().remote_uri,
        print "is", self.call.info().state_text,
        print "last status code ==", self.call.info().last_code,

        # Detect disconnection events for SIP calls.
        if self.call.info().state == pjsua.CallState.DISCONNECTED:
            current_call = None
            print "SIP call has been disconnected."

    # Method that implements state changes in the media processor.
    def on_media_state(self):
        if self.call.info().media_state == pjsua.MediaState.ACTIVE:
            # Capture the call_slot for the currently active call.
            call_slot = self.call.info().conf_slot

            # Sleep for a little while to give the callee a chance to pick
            # up the phone.
            time.sleep(DELAY_BEFORE_PLAYBACK)

            # Connect the media player to the call and vice versa.
            pjsua.Lib.instance().conf_connect(wav_player_slot, call_slot)
            pjsua.Lib.instance().conf_connect(call_slot, wav_player_slot)
            print "Media processor is now active."
        else:
            print "Media processor is now inactive."

# Functions.

# Core code...
# Set up the command line argument parser.
argparser = argparse.ArgumentParser()
argparser.add_argument('--production', action='store_true',
    help="Don't try to initialize a sound device when won't exist anyway.")
argparser.add_argument('--phone-number', action='store', default='2064560649',
    help="Specify a phone number to call (no dashes, e.g., 2125551212).")
argparser.add_argument('--message', action='store',
    help="Full path to a .wav file to play back into the call.  Required.")
argparser.add_argument('--username', action='store',
    help="Optional username to add to outbound SIP packets.")

# Parse the command line args, if any.
args = argparser.parse_args()
if args.production:
    production_mode = True
    print "Production mode enabled.  No sound hardware enabled."

if args.phone_number:
    phone_number = args.phone_number

if not args.message:
    print "ERROR: You must specify a path to a .wav file to play into your call."
    sys.exit(1)
else:
    # Make sure the file exists.  ABEND if not.
    if not os.path.exists(args.message):
        print "ERROR: That file doesn't exist.  Did you get the path right?"
        sys.exit(1)
    else:
        outbound_message = args.message

if args.username:
    outbound_username = args.username

# Allocate an instance of the PJSUA library interface.
lib = pjsua.Lib()

# Try to initialize the PJSUA library interface, set a transport, and start
# it up.
try:
    lib.init()
    lib.create_transport(pjsua.TransportType.UDP)
    lib.start()

    # In production mode (read: running on a VPS) disable the default sound
    # device because there won't be one, anyway.
    if production_mode:
        lib.set_null_snd_dev()

    # Register with the SIP provider.
    account = lib.create_account(pjsua.AccountConfig(HOST, USERNAME, PASSWORD,
        outbound_username))

    # Attach a callback to the account object so we can keep track of its
    # status.
    account_callback = MyAccountCallback(account)
    account.set_callback(account_callback)

    # Start the account callback object so it'll receive events.
    account_callback.wait()

    # Display registration status.
    print "\n"
    print "SIP registration complete, status=", account.info().reg_status
    print account.info().reg_reason
    print "\n"

    # Create a SIP URI for the destination to call.
    call_destination = 'sip:' + phone_number + '@' + HOST

    # Allocate a .wav playback object.
    wav_player = lib.create_player(outbound_message)
    wav_player_slot = lib.player_get_slot(wav_player)

    # Try to place a call to the generated SIP URI.
    print "Placing call to ", call_destination, "..."
    try:
        account.make_call(call_destination, cb=MyCallCallback())
    except pjsua.Error, call_error:
        print "ERROR: Unable to place call: ", call_error

    # Calculate the duration of the .wav file to play into the call.
    with contextlib.closing(wave.open(outbound_message, 'r')) as wav_file:
        wav_frames = wav_file.getnframes()
        wav_rate = wav_file.getframerate()
        wav_duration = wav_frames / float(wav_rate)
        wav_duration = int(round(wav_duration)) + 1

    # Sleep that long to wait for the .wav file to finish.
    time.sleep(wav_duration)

except pjsua.Error, err:
    print "ERROR: Unable to initalize PJSUA interface: ", err

# Tear down the library interface objects.
account.delete()
account = None

lib.destroy()
lib = None

# Fin.
sys.exit(0)

