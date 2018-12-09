This is a bot which takes URLs submitted via XMPP ("Botname, index https://example.com/foo.html") and submits it to the search engines and web page indexing sites configered in web_indexing_bot.conf.  As a proof-of-concept I've included a configuration stanza for [YaCy](http://yacy.de/), a distributed, open source search engine which has a couple of use cases.

When using a YaCy instance as one of the search engines you're submitting links to, you'll probably want to ensure the following if you have concerns about random people on the Net submitting links to your instance:

* Set it for "Search portal for your own web pages" unless you want to participate in the greater YaCy network.  Depending on where your YaCy instance is running, you may want to.  It's your call.
* I highly recommend that you run a copy of the exocortex_xmpp_bridge and the web_index_bot on the same server as YaCy so that you can set the "Access from localhost without an account" option on YaCy's User Administration page.  Otherwise you'll get 401 (Authorization Required) HTTP errors, so you'll have to hack this bot's config file to work around that.  However, you'll also want to think about password protecting your YaCy node's admin pages with a different config option so nobody can roll in there and torch your indices.

Included with the bot is a sample [supervisord](http://supervisord.org/) configuration file which will automatically start and manage the bot for you if you happen to be using it on your system.  It's much easier to wrangle than a huge .screenrc file, initscripts, or systemd service files.  If you want to use this file, install supervisord on the system, ideally from the default package repository (it's usually called **supervisor**).  Enable and start the supervisord service per your distribution's instructions.  Copy the **web_index_bot.conf.supervisord** file as **web_index_bot.conf** into your system's supervisord supplementary configuration file directory; on Raspbian this is */etc/supervisor/conf.d*.  Edit the file so that paths in the *command* and *directory* directives reflect where you checked out the source code.  Also set the *user* directive to the username that'll be running this bot (probably yourself).  For example, the */etc/supervisor/conf.d/web_index_bot.conf* file on my test machine looks like this:

```[program:webindexbot]
command=/home/pi/exocortex-halo/web_index_bot/run.sh
directory=/home/pi/exocortex-halo/web_index_bot
startsecs=30
user=pi
redirect_stderr=true
process_name=webindexbot
startretries=0
```

Then tell supervisord to look for new configuration directives and automatically start anything it finds: **sudo supervisorctl update**

supervisord will read the new config file and start Web Index Bot for you.
