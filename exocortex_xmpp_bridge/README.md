Please note: I've ported this code to [Python 3](https://pythonclock.org) because Python v2.x will not be maintained past 1 January 2020.ev.  Everything henceforce will be written with that assumption.

exocortex_xmpp_bridge.py is a bot that does two things: It logs into an XMPP server using a dedicated account, and it presents message queues accessible via REST API rails that other bots can push and pull events through.

It requires the following Python modules providing XMPP protocol support which, if you they aren't available in your distro's default package repo (they are in Ubuntu v14.04 Server LTS) you'll have to install on your own.  The modules are:

* [sleekxmpp](https://github.com/fritzy/SleekXMPP)
* [dnspython](http://www.dnspython.org/)
* [pyasn1](https://github.com/etingof/pyasn1)
* pyasn1_modules

If they're not I highly recommend installing them into a (venv)[https://docs.python.org/3/tutorial/venv.html] to keep from splattering them all over your file system.  Here's one way to do it (and, in fact, is the recommended and supported method):

* `cd exocortex_halo/exocortex_xmpp_bridge`
* `python3 -m venv env`
* `source env/bin/activate`
* `pip install -r requirements.txt`

You'll have to run `source env/bin/activate` every time you want to start up the XMPP bridge bot.  I've included a shell script called `run.sh` which does this automatically for you.

There is no defined format for commands sent to the message queues of this bot.  As long as they are well-formed (JSON)[https://json.org] documents and the message queues exist (i.e., are configured in exocortex_xmpp_bridge.conf) anything that knows where to look can hit each endpoint as many times as it likes, and it'll get back one (1) JSON document per hit; it's on its own to properly parse and utilize that JSON document.  If the message queue is empty it'll get back a document that looks like this, so write your code to handle this case:

```
{"command": "no commands"}
```

The XMPP bridge will always have a rail called */replies* which anything (from a bot to an evocation of (cURL)[https://curl.haxx.se]) on the sever can send arbitrary messages to.  This text will be relayed to the bot's owner as usual.  You can also use this to get as creative as you want.

If a message queue/API rail doesn't exist, you'll get a JSON document like this:

```
{agent: "not found"}
```

If you make a request to / (just a forward slash) you'll get a JSON document displaying all of the configured message queues running at that time.

Commands are returned in FIFO (first-in-first-out) order from each queue.

I've included a .service file (`xmpp_bridge.service`) in case you want to use [systemd](https://www.freedesktop.org/wiki/Software/systemd/) to manage your bots.  I've written the .service file specifically so that it can be run in [user mode](https://wiki.archlinux.org/index.php/Systemd/User) and will not require elevated permissions of any kind.  Here is the process for setting it up and using it:

* `mkdir -p ~/.config/systemd/user/`
* `cp ~/exocortex-halo/exocortex_xmpp_bridge/xmpp_bridge.service ~/.config/systemd/user/`
* Configure the XMPP bridge by making a copy of `exocortex_xmpp_bridge.conf.example` to `exocortex_xmpp_bridge.conf` and editing the file.
* Start the XMPP bridge: `systemctl start --user xmpp_bridge.service`
  * You should see something like this if it worked:
```
[drwho@windbringer exocortex_xmpp_bridge]$ ps aux | grep [e]xocortex
drwho     6039  0.1  0.1 459332 24572 ?        Ssl  14:15   0:06 python2 /home/drwho/exocortex-halo/exocortex_xmpp_bridge/exocortex_xmpp_bridge.py
```
* Set the XMPP bridge to start automatically on boot: `systemctl enable --user xmpp_bridge.service`
  * You should see something like this if it worked:
```
[drwho@windbringer exocortex_xmpp_bridge]$ ls -alF ~/.config/systemd/user/default.target.wants/
total 8
drwxr-xr-x 2 drwho drwho 4096 Jan 26 14:16 ./
drwxr-xr-x 3 drwho drwho 4096 Jan 26 14:15 ../
lrwxrwxrwx 1 drwho drwho   52 Jan 26 14:16 xmpp_bridge.service -> /home/drwho/.config/systemd/user/xmpp_bridge.service
```
