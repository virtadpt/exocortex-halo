Please note: I've ported this code to [Python 3](https://pythonclock.org) because Python v2.x will not be maintained past 1 January 2020.ev.  Everything henceforce will be written with that assumption.

This is a bot which takes URLs submitted via XMPP ("Botname, index https://example.com/foo.html") and submits it to the search engines and web page archival sites configured in the `web_indexing_bot.conf` file.  As a proof-of-concept I've included a configuration stanza for [YaCy](http://yacy.de/), a distributed, open source search engine.

This bot requires the [requests](http://docs.python-requests.org/en/master/) Python module.  I highly recommend installing it into a [venv](https://docs.python.org/3/tutorial/venv.html) to keep from splattering files all over your system.  Here's one way to do it (and, in fact, is the recommended and supported method):

* `cd exocortex_halo/web_index_bot`
* `python3 -m venv env`
* `source env/bin/activate`
* `pip install -r requirements.txt`

You'll have to run `source env/bin/activate` every time you want to start the Web Index Bot.  I've included a shell script called `run.sh` which does this automatically for you.

When using a YaCy instance as one of the search engines you're submitting links to, you'll probably want to ensure the following if you have concerns about random people on the Net submitting links to your instance:

* Set it for "Search portal for your own web pages" unless you want to participate in the greater YaCy network.  Depending on where your YaCy instance is running, you may want to.  It's your call.
* I highly recommend that you run a copy of the [exocortex_xmpp_bridge](https://github.com/virtadpt/exocortex-halo/tree/master/exocortex_xmpp_bridge) and the Web Index Bot on the same server as YaCy so that you can set the "Access from localhost without an account" option on YaCy's User Administration page.  Otherwise you'll get 401 (Authorization Required) HTTP errors and you'll have to hack this bot's config file to work around that.  However, you'll also want to think about password protecting your YaCy node's admin pages with a different config option so nobody can roll in there and torch your indices.

I've also included a .service file (`web_index_bot.service`) in case you want to use [systemd](https://www.freedesktop.org/wiki/Software/systemd/) to manage your bots.  Unlike supervisord, systemd can actually manage dependencies of system services, and as much as I find the service irritating it does a fairly decent job of this.  I've written the .service file specifically such that it can be run in [user mode](https://wiki.archlinux.org/index.php/Systemd/User) and will not require elevated permissions of any kind.  Here is the process for setting it up and using it:

* `mkdir -p ~/.config/systemd/user/`
* `cp ~/exocortex-halo/web_index_bot/web_index_bot.service ~/.config/systemd/user/`
* You configure the XMPP bridge by making a copy of `web_index_bot.conf.example` to `web_index_bot.conf` and editing it.
* Starting the XMPP bridge: `systemctl start --user web_index_bot.service`
  * You should see something like this if it worked:
```
[drwho@windbringer web_index_bot]$ ps aux | grep [w]eb_index
drwho     6039  0.1  0.1 459332 24572 ?        Ssl  14:15   0:06 python /home/drwho/exocortex-halo/web_index_bot/web_index_bot.py
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
* Ensure that systemd in --user mode will start on boot and run even when you're not logged in: `loginctl enable-linger <your username here>`
