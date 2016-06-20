# exocortex-halo
Various and sundry additional pieces of software I've written to incorporate into my exocortex that extend the functionality of Huginn (https://github.com/cantino/huginn).  You never know what you're going to find in here because I do a lot of idiosyncratic stuff and as I get ideas for functionality to incorporate new things will appear in here.  Not all of them will make sense.  I've tried to use as few external modules as possible; in general, if a particular module comes with a default Python v2.7 install I prefer it over somebody else's.  I'm developing on Arch Linux (64-bit) and Ubuntu Server v14.04 LTS.  For times where a module isn't included by default (or available in the default package repositories) I've included a requirements.txt file, suitable for use with virtualenv (https://virtualenv.readthedocs.org/en/latest/) and pip (https://pypi.python.org/pypi/pip).

beta_fork/
A more generic implementation of irc_bot/.  Again, there is a REST API server which maintains a Markov brain.  This simplifies writing other kinds of bots (IRC, Slack, XMPP, Twitter, et cetera) by breaking out the chat part.  Right now only a proof-of-concept bot (an IRC bot) exists; it should serve as an example of writing other kinds of chatbots that plug into it.  This is, again, in the experimental stage and doesn't have a lot of features (like databases of stuff to monitor channels for) yet.

exocortex_gps_mapper/

A relatively simple web application that uses web.py (http://webpy.org/) to implement a REST API.  An application running on a smartphone periodically pings an endpoint with its current GPS coordinates.  Contacting the web app throws up a Google Map with the GPS coordinates.  It's far from complete because I don't know JavaScript but right now it's enough for my purposes.

exocortex_sip_client/

A command line application that can be used to place calls into the PSTN through a Voice-Over-IP provider and play a .wav file as the call.  I designed it to work as part of a larger toolkit of utilities.  Requires PJSIP (http://www.pjsip.org/) (but NOT PJSUA) to implement SIP functionality.

Special thanks to The Test Call (http://thetestcall.blogspot.com/) for providing the default phone number for debugging.  I got kind of tired of rickrolling myself...

exocortex_xmpp_bridge/

A daemon that logs into an arbitrary XMPP server on one side and implements a dynamic message queue internally.  The idea is that you should be able to send chat messages to the XMPP address the daemon logs into (it checks to see if they are from the bot's registered owner) and puts them into its internal message queues.  The other side is a REST API service that other agents and bots can poll for commands.  If you write a bot and you want to send it commands via XMPP, this is one way of going about it.  I've tried to make the REST endpoints as self-documenting (wget and curl are enough to poke at it) and as extensible as possible (as long as you know what kind of JSON you want to get out of it, you should be able to do whatever you want).  There is nothing preventing a single Exocortex from running multiple instances of this daemon on multiple hosts under different user@xmpp.host.com accounts; in fact, I strongly recommend doing so.

irc_bot/
A bot that logs into an arbitrary IRC server and joins one (right now) or more channels (or it will, anyway), and listens to what gets posted.  The bot has a Markov engine (and will eventually have a Dissociated Press engine) for occasionally responding to things that are said in the channel.  The bot will also have a keyword detector that maintains a user-supplied list of interesting things to monitor for, picks up on them, and will report them to the user when they're said.  Eventually, this bot will log into an XMPP server using a unique account and report that way; in addition the user will be able to "speak through" the bot into the channel to respond.  I haven't gotten to the point where I

I used this as the basis for the bot: http://wiki.shellium.org/w/Writing_an_IRC_bot_in_Python

This bot is still in the experimental stage, I only threw it in here when I did so that someone else could easily look at the code.  It's really undeveloped so don't expect anything from it just yet.  It'll probably be rewritten using a real IRC protocol implementation of some kind.

web_search_bot/
A bot that periodically polls a REST API service implementing its message queue (in this case, exocortex_xmpp_bridge/) looking for commands and search requests.  It carries out those web search requests (configured in web_search_bot.conf), extracts and packages the URLs, and either sends them to a Huginn webhook (by default) or e-mails them to an arbitrary e-mail address.

