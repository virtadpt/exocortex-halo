This is a relatively simple bot that is part of the Exocortex Halo (https://github.com/virtadpt/exocortex-halo) project which operates in concert with other bots to implement fire-and-forget web search requests.  The intended use case is this: While out and about without a laptop, use an XMPP client running on a phone to send a command of the form "<agent>, top twenty hits for <some weird search term>."  These commands are picked up by exocortex_xmpp_bridge.py and stored in an message queue that is periodically polled (by default, once a minute) by this bot.  web_search_bot.py extracts a message with the search request from its mssage queue, parses it, assembles the actual search request, and runs a search through an instance of Searx (https://github.com/asciimoo/searx) defined in web_search_bot.conf.

You're probably wondering why I stripped out the "define your own search engines and parsers in the config file" functionality, which earlier releases of this bot had.  That's because I got tired of maintaining lists of search engines and hyperlinks to strip out.  They change often enough that this got to be annoying and limiting.  Searx does much of this on its own, plus it returns search results with rankings as JSON, which simplifies working with the results immensely.  After some testing I find that it returns much more reliable and useful search results than my own code did.

So, [go install Searx](https://asciimoo.github.io/searx/dev/install/installation.html) but don't bother with uwsgi or putting it behind a reverse proxy; just have it listen on 127.0.0.1 on some port you're not using (8888/tcp by default).

web_search_bot.py is also capable of e-mailing search terms to an address specified in the command.  For example, "<agent>, send you@example.com top twenty hits for <some weird search term>"

web_search_bot.py currently only supports up to fifty (50) search results.  Specifying an invalid number causes it to default to ten (10).

web_index_bot.py is a bot which does the reverse - when you send it a URL it submits it to whatever search engines you have defined in its configuration file.  This could be something like an instance of [YaCy](http://yacy.de/) running on the same host or it could be [the Internet Archive's Wayback Machine](https://web.archive.org/).

Included with the bot is a sample [supervisord](http://supervisord.org/) configuration file which will automatically start and manage the bot for you if you happen to be using it on your system.  It's much easier to wrangle than a huge .screenrc file, initscripts, or systemd service files.  If you want to use this file, install supervisord on the system, ideally from the default package repository (it's usually called **supervisor**).  Enable and start the supervisord service per your distribution's instructions.  Copy the **web_search_bot.conf.supervisord** file as **web_search_bot.conf** into your system's supervisord supplementary configuration file directory; on Raspbian this is */etc/supervisor/conf.d*.  Edit the file so that paths in the *command* and *directory* directives reflect where you checked out the source code.  Also set the *user* directive to the username that'll be running this bot (probably yourself).  For example, the */etc/supervisor/conf.d/web_search_bot.conf* file on my test machine looks like this:

```[program:websearchbot]
command=/home/pi/exocortex-halo/web_search_bot/run.sh
directory=/home/pi/exocortex-halo/web_search_bot
startsecs=30
user=pi
redirect_stderr=true
process_name=websearchbot
startretries=0
```

Then tell supervisord to look for new configuration directives and automatically start anything it finds: **sudo supervisorctl update**

supervisord will read the new config file and start Web Search Bot for you.

I've also included a .service file (`web_search_bot.service`) in case you want to use [systemd](https://www.freedesktop.org/wiki/Software/systemd/) to manage your bots.  Unlike supervisord, systemd can actually manage dependencies of system services, and as much as I find the service irritating it does a fairly decent job of this.  I've written the .service file specifically such that it can be run in [user mode](https://wiki.archlinux.org/index.php/Systemd/User) and will not require elevated permissions of any kind.  Here is the process for setting it up and using it:

* `mkdir -p ~/.config/systemd/user/`
* `cp ~/exocortex-halo/web_search_bot/web_search_bot.service ~/.config/systemd/user/`
* You configure the XMPP bridge by making a copy of `web_search_bot.conf.example` to `web_search_bot.conf` and editing it.
* Starting the XMPP bridge: `systemctl start --user web_search_bot.service`
  * You should see something like this if it worked:
```
[drwho@windbringer web_search_bot]$ ps aux | grep [w]eb_search
drwho     6039  0.1  0.1 459332 24572 ?        Ssl  14:15   0:06 python2 /home/drwho/exocortex-halo/web_search_bot/web_search_bot.py
```
* Setting the web search bot to start automatically on system boot: `systemctl enable --user web_search_bot.service`
  * You should see something like this if it worked:

```
[drwho@windbringer web_search_bot]$ ls -alF ~/.config/systemd/user/default.target.wants/
total 8
drwxr-xr-x 2 drwho drwho 4096 Jan 26 14:16 ./
drwxr-xr-x 3 drwho drwho 4096 Jan 26 14:15 ../
lrwxrwxrwx 1 drwho drwho   52 Jan 26 14:16 web_search_bot.service -> /home/drwho/.config/systemd/user/web_search_bot.service
```

