# exocortex-halo
Various and sundry additional pieces of software I've written to incorporate into my exocortex that extend the functionality of Huginn (https://github.com/huginn/huginn).  You never know what you're going to find in here because I do a lot of idiosyncratic stuff and as I get ideas for functionality to incorporate new things will appear in here.  Not all of them will make sense.  I've tried to use as few external modules as possible; in general, if a particular module comes with a default Python v3.x install I prefer it over somebody else's.  I'm developing on Arch Linux, Ubuntu Server v18.04 LTS (both 64-bit), and Raspbian.  For times where a module isn't included by default (or available in default package repositories) I've included a requirements.txt file, suitable for use with [venv](https://docs.python.org/3/tutorial/venv.html/) and [pip](https://pypi.python.org/pypi/pip).

## deprecated/
I move bots that are officially deprecated (i.e., no longer in development) into here rather than delete them.  You're welcome to pick them up and work on them if you want, or just refer to them as examples.

## beta_fork/
A more generic implementation of irc_bot/.  Again, there is a REST API server which maintains a Markov brain; hypothetically speaking, you could swap out the Markov engine for any other kind of conversation engine you want.  This simplifies writing other kinds of bots (IRC, Slack, XMPP, Twitter, et cetera) by breaking out the chat part into a separate process.  Right now only a proof-of-concept bot (an IRC bot) exists; it should serve as an example of writing other kinds of chatbots that plug into it.  This is, again, in the experimental stage and doesn't have a lot of features (like databases of stuff to monitor channels for) yet.

## command_line_messager/
A relatively simple command line utility which lets you send arbitrary text to the XMPP bridge without needing to build an actual bot.  For example, if you wanted cron jobs to send you messages over XMPP rather than email, this is what you could use just by piping stdout and stderr through it.

## copy_bot/
A bot that pretty much does what it says on the tin.  Send it a message that tells it to copy a file or files from one directory to another, and it'll happily do that for you.  I use it to remotely deploy code from home but there are undoubtedly other uses you can put it to.

## download_bot/
A bot that downloads files when you send it URLs in an XMPP message.  I use this bot to grab files I want to read later and store them on my fileserver at home.  This bot can also load [youtube-dl](https://github.com/ytdl-org/youtube-dl) if it's available and save streaming videos to the server.  Do so by installing the module into the same venv download_bot uses (`pip3 install youtube_dl`) and restart the bot.  If [ffmpeg](https://ffmpeg.org/) is also installed (which is almost always available in your distro's package repository) this bot can save just the audio from those video streams as .mp3 files.

## exocortex_gps_mapper/
A relatively simple web application that uses [web.py](http://webpy.org/) to implement a REST API.  An application running on a smartphone periodically pings an endpoint with its current GPS coordinates.  Contacting the web app throws up a Google Map with the GPS coordinates.  It's far from complete because I don't know JavaScript but right now it's enough for my purposes. (DEPRECATED)

## exocortex_sip_client/
A command line application that can be used to place calls into the PSTN through a Voice-Over-IP provider and play a .wav file as the call.  I designed it to work as part of a larger toolkit of utilities.  Requires [PJSIP](http://www.pjsip.org/) (but NOT PJSUA) to implement SIP functionality. (DEPRECATED)

Special thanks to [The Test Call](http://thetestcall.blogspot.com/) for providing the default phone number for debugging.  I got kind of tired of rickrolling myself...

## exocortex_xmpp_bridge/
A daemon that logs into an arbitrary XMPP server on one side and implements dynamic message queues.  The idea is that you can send chat messages to the XMPP address the daemon logs into (it checks to see if they are from the bot's registered owner (which is probably you, dear reader)) and puts them into one of its internal message queues.  The other side is a REST API service that other agents and bots can poll for commands.  If you write a bot and you want to send it commands via XMPP, this is one way of going about it.  I've tried to make the REST endpoints as self-documenting ([wget](https://www.gnu.org/software/wget/) and [curl](https://curl.haxx.se/) are enough to poke at it) and as extensible as possible (as long as you know what kind of JSON you want to get out of it, you should be able to do whatever you want).  There is nothing preventing a single Exocortex from running multiple instances of this daemon on multiple hosts with different user@xmpp.host.com accounts; in fact, I strongly recommend doing so.

## hmac_a_tron/
This bot does one thing and one thing only: It implements [HMAC](https://en.wikipedia.org/wiki/HMAC) of data for HTTP requests to interact with some REST APIs.  It's kind of annoying that I had to build a separate bot to implement this, but what can you do.

## irc_bot/
A bot that logs into an arbitrary IRC server and joins one a channel and listens to what gets posted.  The bot has a Markov engine (and will eventually have a Dissociated Press engine) for occasionally responding to things that are said in the channel.  The bot will also have a keyword detector that maintains a user-supplied list of interesting things to monitor for, picks up on them, and will report them to the user when they're said.  Eventually, this bot will log into an XMPP server using a unique account and report that way; in addition the user will be able to "speak through" the bot into the channel to respond.

I used [this](http://wiki.shellium.org/w/Writing_an_IRC_bot_in_Python) as the basis for writing the bot.

This bot is still in the experimental stage, I only threw it in here when I did so that someone else could easily look at the code.  It's really undeveloped so don't expect anything from it just yet.  It'll probably be rewritten using a real IRC protocol implementation of some kind.  (DEPRECATED)

## kodi_bot/
As an experiment in writing command parsers in new and exciting (and confusing) ways, this is an attempt at writing a bot to remotely control a [Kodi](https://kodi.tv/) server.  The parser is mostly done, the text [corpora](https://wiki.apache.org/spamassassin/PluralOfCorpus) are mostly done, but interacting with the [Kodi API](https://kodi.wiki/view/JSON-RPC_API) is not.  Please help?

## paywall_breaker/
This bot was designed out of frustration with sites that throw up paywalls on articles which have critical information (such as specifics of vulnerabilities that involve remove code execution).  The bot takes URLs from an XMPP bridge instance and downloads the page by spoofing the user agent of a search engine's spider (configurable).  The page is parsed into text and copied into a new page in an instance of [Etherpad-Lite](https://github.com/ether/etherpad-lite) where it can be read later.  When the page is archived the configured user will receive an e-mail with a direct link to the Etherpad page.  The new page will undoubtedly need some editing to clean it up but most of the time you'll get the content you're after.  I highly recommend requiring authentication in front of your Etherpad-Lite instance to minimize the possibility that someone might abuse it.  Here are the Etherpad-Lite plugins that I find very useful:

* ep_list_pads
* ep_public_view
* ep_push2delete
* ep_set_title_on_pad
* ep_simpletextsearch

Note: Paywall Breaker is (DEPRECATED).  I use [Wallabag](https://github.com/wallabag/wallabag) these days, and it works much better.

## shaarli_bot/
This is a fairly simple bot which lets you search on fulltext or tags in a [Shaarli](https://github.com/shaarli/Shaarli) instance using the API.  Regardless of what you use Shaarli for (bookmarks, [card catalogue](https://en.wikipedia.org/wiki/Library_catalog), what have you) this bot will let you search the collection.  As a proof of concept I've also included [a utility](shaarli_bot/lt_to_shaarli.py) which will take a [JSON export](https://www.librarything.com/more/import) from [LibraryThing](https://www.librarything.com/), reformat it, and upload the data into Shaarli.

## smtp_bridge/
For situations when you have machines which can't send outbound e-mail easily (for example, if your ISP blocks it) this bot will be of use.  It starts up and pretends to be an [SMTP](https://www.geeksforgeeks.org/simple-mail-transfer-protocol-smtp/) server running on the system, not unlike [Exim](https://www.exim.org/) or [Postfix](http://www.postfix.org/).  However, rather than sending the e-mail it reformats the message and sends it instead over the Exocortex XMPP bridge, where you will receive it in your [Jabber client](https://jabber.at/clients/).  Please note that by default this bridge [will need to be started as the root user](https://www.w3.org/Daemon/User/Installation/PrivilegedPorts.html), but after opening the [default SMTP port](https://www.mailgun.com/blog/which-smtp-port-understanding-ports-25-465-587) (25/tcp) it will drop privileges to the user and group in the config file (by default, nobody and nobody) for security reasons.

## system_bot/
System Bot is an all-in-one system monitoring bot.  It watches (among other things) system load, disk and memory usage, system uptime, and any processes you configure it to watch.  You can query various aspects of your system's status or it can run in the background and send you messages via the XMPP bridge if anything starts going wrong.  I run this bot on all of my machines and it's been a lifesaver time and again.  I strongly suggest that you name your System Bots the same as the hostnames they run on, but do whatever works best for you.

## web_index_bot/
A bot that sends URLs given to it to the web indexing and archival sites listed in its configuration file.  The examples I've provided are a local [YaCy](http://yacy.net/) server, [Gigablast](http://www.gigablast.com/), [the Wayback Machine](https://web.archive.org/), and [Webcitation](http://www.webcitation.org/).  My original use case was the first one (YaCy) but I figured that it should be extensible so people could find other uses for it.  As long as you can send a URL to an API, you can add it to this bot.

## web_search_bot/
A bot that periodically polls its message queue on the XMPP bridge looking for search requests.  It carries out those web search requests by relaying them to a copy of [Searx](https://github.com/asciimoo/searx), extracts the results, and either sends them back to you via XMPP or to an arbitrary e-mail address.  One can in theory point it any Searx instance out there and get useful results instantly.

# HOWTO

## Get an account on an XMPP server

First, you need a dedicated XMPP (Jabber) account for the XMPP bridge.  You could use a public one like [jabber.ccc.de](http://jabber.ccc.de/), a friend's Jabber server (you'll need at least two XMPP accounts, one for yourself and one for each instance of the XMPP bridge), or you can set up your own on a VPS (they're pretty easy to set up and a more than usable VPS will cost $5-10us per month); again, you'll need at least two accounts on the XMPP server.

## Check out this Git repository.

Clone this repo onto a Linux box you control.  You could use a VPS running at a hosting provider, a Linux box at home, a RaspberryPi, or a full-sized machine someplace.

## Set up exocortex_XMPP_bridge

* `cd exocortex-halo/exocortex_xmpp_bridge/`
* Set up a [Python virtualenv](http://docs.python-guide.org/en/latest/dev/virtualenvs/) to install the XMPP bridge's dependencies into.
 * `virtualenv2 env`
 * Wait...
* Activate the virtualenv
 * `. env/bin/activate`
 * The command line prompt will change - it will start with "(env) "
* Install the dependencies
 * `pip install -r requirements.txt`
* Copy exocortex_xmpp_bridge.conf.example to exocortex_xmpp_bridge.conf and customize it for your environment.  The XMPP username and password you set up for the XMPP bridge need to go in here.  The 'real' names of the bots you plan to associate with this bridge need to go in the 'agents' list at the very end as shown.
* You'll need one instance of exocortex_xmpp_bridge.py for each server you have.  I have multiple instances on different machines, all running different bots.
* Start the XMPP bridge.
 * `python2 ./exocortex_xmpp_bridge.py`

## Log into your admin XMPP account and test the XMPP bridge.

Configure an XMPP client (I kinda like [Profanity](http://profanity.im/)) to log into your personal (admin) XMPP account on the same server the XMPP bridge uses.  Send an IM to your copy of the XMPP bridge and ask it for a status report:

`Robots, report.`

You should get a response something like this:

```
16:53 - me: Robots, report.
16:53 - Bridge : Contents of message queues are as follows:

        Agent Alice: []
        Agent Bob: []
```

This means that the XMPP bridge is up, running, and has set up message queues for the bots you told it to in the configuration file.
