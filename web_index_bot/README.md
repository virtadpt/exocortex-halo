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

I've also included a .service file (`web_index_bot.service`) in case you want to use [systemd](https://www.freedesktop.org/wiki/Software/systemd/) to manage your bots.  Unlike supervisord, systemd can actually manage dependencies of system services, and as much as I find the service irritating it does a fairly decent job of this.  I've written the .service file specifically such that it can be run in [user mode](https://wiki.archlinux.org/index.php/Systemd/User) and will not require elevated permissions of any kind.  Here is the process for setting it up and using it:

* `mkdir -p ~/.config/systemd/user/`
* `cp ~/exocortex-halo/web_index_bot/web_index_bot.service ~/.config/systemd/user/`
* You configure the XMPP bridge by making a copy of `web_index_bot.conf.example` to `web_index_bot.conf` and editing it.
* Starting the XMPP bridge: `systemctl start --user web_index_bot.service`
  * You should see something like this if it worked:
```
[drwho@windbringer web_index_bot]$ ps aux | grep [w]eb_index
drwho     6039  0.1  0.1 459332 24572 ?        Ssl  14:15   0:06 python2 /home/drwho/exocortex-halo/web_index_bot/web_index_bot.py
```
* Setting the web index bot to start automatically on system boot: `systemctl enable --user web_index_bot.service`
  * You should see something like this if it worked:

```
[drwho@windbringer web_index_bot]$ ls -alF ~/.config/systemd/user/default.target.wants/
total 8
drwxr-xr-x 2 drwho drwho 4096 Jan 26 14:16 ./
drwxr-xr-x 3 drwho drwho 4096 Jan 26 14:15 ../
lrwxrwxrwx 1 drwho drwho   52 Jan 26 14:16 web_index_bot.service -> /home/drwho/.config/systemd/user/web_index_bot.service
```

