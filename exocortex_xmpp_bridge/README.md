exocortex_xmpp_bridge.py is a bot that does two things: It logs into an XMPP server using a dedicated account, and it presents message queues accessible via REST API rails that other bots can contact and pull events out of.

It requires the following Python modules providing XMPP protocol support which, if you they aren't available in your distro's default package repo (they are in Ubuntu v14.04 Server LTS) you'll have to install on your own.  The modules are:

* [sleekxmpp](https://github.com/fritzy/SleekXMPP)
* [dnspython](http://www.dnspython.org/)
* [pyasn1](https://github.com/etingof/pyasn1)
* pyasn1_modules

If they're not I highly recommend installing them into a virtualenv to keep from splattering them all over your file system.  Here's one way to do it on an Ubuntu box:

* `sudo apt-get install python2.7-dev`
* `mkdir exocortex_xmpp_bridge`
* `cd exocortex_xmpp_bridge`
* `virtualenv2 env`
* `source env/bin/activate`
* `pip2 install -r requirements.txt`

You'll have to run `source env/bin/activate` every time you want to start up the XMPP bridge bot.  I've included a shell script called `run.sh` which does this automatically for you.

There is no defined format for commands sent to the message queues of this bot.  As long as they are well-formed JSON documents and the message queues exist (i.e., are configured in exocortex_xmpp_bridge.conf) anything that knows where to look can hit each endpoint as many times as it likes, and it'll get back one (1) JSON document per hit; it's on its own to properly parse and utilize that JSON document.  If the message queue is empty it'll get back a document that looks like this, so write your code to handle this case:

```
{"command": "no commands"}
```

The XMPP bridge will always have a rail called */replies* which any bot on the sever can send arbitrary text to.  This text will be relayed to the bot's owner as usual.  You can also use this to get creative with curl or whatever else you want.

If a message queue/API rail doesn't exist, you'll get a JSON document like this:

```
{agent: "not found"}
```

If you make a request to / (just a forward slash) you'll get a JSON document displaying all of the configured message queues running at that time.

Commands are returned in FIFO (first-in-first-out) order.

