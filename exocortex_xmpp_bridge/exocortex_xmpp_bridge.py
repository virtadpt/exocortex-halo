#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# exocortex_xmpp_bridge.py - A microservice in Python that logs into an XMPP
#   server with credentials in a configuration file, connects to an MQTT broker,
#   and listens for messages sent to the account by a designated owner.  Each
#   message must have the name of the agent the command is for.  The
#   microservice pushes messages into the destination agent's queue to be
#   processed later.  Unmatched agents are silently (to the sender) dropped.

# This is an unholy combination of OO and not-OO, and I'm sorry.  I'm so, so
# sorry.  Mosquitto doesn't lend itself to OO very well.

# TODO:

# By: The Doctor <drwho at virtadpt dot net>
#     0x807B17C1 / 7960 1CDC 85C9 0B63 8D9F  DD89 3BD8 FF2B 807B 17C1

# License: GPLv3

import ConfigParser
import logging
import mosquitto
from optparse import OptionParser
import sleekxmpp
import sys

class XMPPBot(sleekxmpp.ClientXMPP):

    # Initializer method for the XMPPBot class.
    def __init__(self, jid, password):
        super(XMPPBot, self).__init__(jid, password)

        # Set up an event handler for when the XMPPBot starts up.
        self.add_event_handler('session_start', self.start)

        # Set up an event handler that processes incoming messages.
        self.add_event_handler('message', self.message)

    # Method that fires as an event handler when XMPPBot starts running.
    def start(self, event):

        # Needed to tell the XMPP server "I'm here!"
        self.send_presence()

        # If the XMPP account has a roster ("Buddy list") on the server, pull
        # it.
        # Note: This can time out under bad conditions.  Consider putting it
        # inside a try/except to retry or error out.
        self.get_roster()

        logger.debug("I've successfully connected to the XMPP server.")

    # Method that fires as an event handler when an XMPP message is received
    # from someone
    def message(self, msg):
        message_body = ""
        agent = ""
        command = ""

        # Test to see if the message came from the agent's owner.  If it did
        # not, drop the message and return.
        if msg['from'] != owner:
            logger.warn("Received a message from someone that isn't authorized.")
            return

        # Potential message types: normal, chat, error, headline, groupchat
        if msg['type'] in ('normal', 'chat'):
            # Extract the XMPP message body for processing.
            message_body = msg['body']

            # Split off the part of the sentence before the first comma or the
            # first space.  That's where the name of the agent can be found.
            # Bad agent names wind up in spurious message queues, and will
            # eventually time out and be deleted by the MQTT broker.
            if ',' in message_body:
                agent = message_body.split(',')[0]
            else:
                agent = message_body.split(' ')[0]

            # Extract the command to the agent and clean it up.
            command = message_body.split(',')[1]
            command = command.strip()
            command = command.strip('.')
            command = command.lower()
            logger.debug(command)

            # Push the command into the agent's message queue.
            my_queue = queue + "/" + agent
            mosquitto_client.publish(my_queue, payload=command)

# Figure out what to set the logging level to.  There isn't a straightforward
# way of doing this because Python uses constants that are actually integers
# under the hood, and I'd really like to be able to do something like
# loglevel = 'logging.' + loglevel
# I can't have a pony, either.  Takes a string, returns a Python loglevel.
def process_loglevel(loglevel):
    if loglevel == 'critical':
        return 50
    if loglevel == 'error':
        return 40
    if loglevel == 'warning':
        return 30
    if loglevel == 'info':
        return 20
    if loglevel == 'debug':
        return 10
    if loglevel == 'notset':
        return 0

# Start of the Mosquitto MQTT client stuff.

# Callback handler for when the agent connects to a broker.  Fires when it
# receives a CONNACK event.
def on_connect(client, userdata, rc):
    logger.debug("I'm connected to MQTT broker " + host + " " + port + "/tcp.")

    # Subscribe to the MQTT queue we'll be publishing messages to because, if
    # we get disconnected mosquitto will automatically reconnect, and it'll
    # have to resubscribe.
    mosquitto_client.subscribe(queue + "/#")

    # Send an "It's alive!  It's alive!" message to the MQTT broker.
    my_queue = queue + "/exocortex_xmpp_bridge.py"
    mosquitto_client.publish(my_queue, payload="I have connected.")

# Callback handler for when the agent disconnects from a broker.
def on_disconnect(client, useradata, rc):
    logger.debug("I am no longer connected to MQTT broker " + host + " " + port + "/tcp.")

# Callback handler that fires when a message is received from a broker.
def on_message(client, useradata, msg):
    # Fields of msg we care about: payload, topic (name of the queue)
    logger.debug("I've received a message on " + msg.topic + ": " + msg.payload)

# Core code...
if __name__ == '__main__':
    # If we're running in a Python environment earlier than v3.0, set the
    # default text encoding to UTF-8 because XMPP requires it.
    if sys.version_info < (3, 0):
        reload(sys)
        sys.setdefaultencoding('utf-8')

    # Instantiate a command line options parser.
    optionparser = OptionParser()

    # Define command line switches for the bot, starting with being able to
    # specify an arbitrary configuration file for a particular bot.
    optionparser.add_option('-c', '--conf', dest='configfile', action='store',
        type='string', help='Specify an arbitrary config file for this bot.  Defaults to exocortex_xmpp_bridge.conf.')

    # Add a command line option that lets you override the config file's
    # loglevel.  This is for kicking a bot into debug mode without having to
    # edit the config file.
    optionparser.add_option('-l', '--loglevel', dest='loglevel', action='store',
        help='Specify the default logging level of the bot.  Choose from CRITICAL, ERROR, WARNING, INFO, DEBUG, NOTSET.  Defaults to INFO.')

    # Add a command line option that lets you override the MQTT host specified
    # in the configuration file.
    optionparser.add_option('--host', dest='host', action='store',
        help='Specify the IP address the web service should listen on.  Defaults to localhost.')

    # Add a command line option that lets you override the MQTT port specified
    # in the configuration file.
    optionparser.add_option('-p', '--port', dest='port', action='store',
        help='Specify the TCP port the web service should listen on.  Defaults to 1883/tcp.')

    # Add a command line option that lets you override the MQTT queue specified
    # in the configuration file.
    optionparser.add_option('--queue', dest='queue', action='store',
        help='Specify the MQTT queue messages get published to.  Defaults to agents/.')

    # Parse the command line args.
    (options, args) = optionparser.parse_args()

    # Read the configuration file.  There is a command line argument for
    # specifying a configuration file, but it defaults to taking the name
    # of the bot and appending '.conf' to it.  Then load it into a config file
    # parser object.
    config = ConfigParser.ConfigParser()
    if options.configfile:
        config.read(options.configfile)
    else:
        config.read('exocortex_xmpp_bridge.conf')
    conf = config.sections()[0]

    # Get configuration options from the configuration file.
    owner = config.get(conf, 'owner')
    username = config.get(conf, 'username')
    password = config.get(conf, 'password')
    host = config.get(conf, 'host')
    port = config.get(conf, 'port')
    queue = config.get(conf, 'queue')

    # Figure out how to configure the logger.  Start by reading from the config
    # file.
    config_log = config.get(conf, 'loglevel').lower()
    if config_log:
        loglevel = process_loglevel(config_log)

    # Then try the command line.
    if options.loglevel:
        loglevel = process_loglevel(options.loglevel.lower())

    # Default to WARNING.
    if not options.loglevel and not loglevel:
        loglevel = logging.WARNING

    # Configure the logger with the base loglevel.
    logging.basicConfig(level=loglevel, format="%(levelname)s: %(message)s")

    # Instantiate a copy of XMPPBot.
    xmppbot = XMPPBot(username, password)

    # Enable the Service Discovery plugin.
    xmppbot.register_plugin('xep_0030')

    # Enable the Ping plugin.
    xmppbot.register_plugin('xep_0199')

    # Instantiate a copy of the Mosquitto client, attach some event handlers,
    # and connect to the broker.
    mosquitto_client = mosquitto.Mosquitto()
    mosquitto_client.on_connect = on_connect
    mosquitto_client.on_disconnect = on_connect
    mosquitto_client.on_message = on_message
    try:
        mosquitto_client.connect(host=host, port=port)
    except:
        logging.fatal("Unable to connect to MQTT broker.  ABENDing.")
        sys.exit(1)

    # Subscribe to the MQTT queue we'll be publishing messages to.  We do it
    # this way because '#' is a wildcard in MQTT but a comment here, and it
    # breaks config files.
    mosquitto_client.subscribe(queue + "/#")

    # Connect to the XMPP server and commence operation.  SleekXMPP's state
    # engine will run inside its own thread because we need to contact other
    # services.
    if xmppbot.connect():
        xmppbot.process(block=False)
    else:
        logging.fatal("Uh-oh - unable to connect to JID " + username + ".")
        sys.exit(1)

    # Start the MQTT client loop.
    mosquitto_client.loop_forever()

# Fin.

