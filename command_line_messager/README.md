Please note: I've ported this code to [Python 3](https://pythonclock.org) because Python v2.x will not be maintained past 1 January 2020.ev.  Everything henceforce will be written with that assumption.

I originally wrote this utility as a way to catch the output of a script running on a server that I can't set up SMTP on, but upon reflection it would also be useful for sending notifications at arbitrary times (say, when someone logs into an account it's executed by their ~/.bashrc script, or with cron as a watchdog).

The requirements for this utility are modest - the only module not included in the basic Python installation is [Requests](http://docs.python-requests.org/en/master/), and that's usually available as a package in your distro's repository.  One way of installing requests:
```
sudo apt-get install -y python3-requests
```

For consistency's sake, a `requests.txt` file is included so that it can be installed into a [venv](https://docs.python.org/3/tutorial/venv.html), but in this one case it's probably overkill.

Online help:
```
usage: send_message.py [-h] [--hostname HOSTNAME] [--port PORT]
                       [--queue QUEUE] [--loglevel LOGLEVEL]
                       [--message [MESSAGE [MESSAGE ...]]]
                       [infile]

A command line utility which allows the user to send text or data to an
instance of the Exocortex XMPP Bridge. An ideal use case for this tool is to
make interactive jobs communicate with the rest of an exocortex.

positional arguments:
  infile                Text stream to send to the XMPP bridge. Give a - to
                        use stdin.

optional arguments:
  -h, --help            show this help message and exit
  --hostname HOSTNAME   Specify the hostname of an XMPP bridge to contact.
                        Defaults to localhost.
  --port PORT           Specify the network port of an XMPP bridge to contact.
                        Defaults to 8003/tcp.
  --queue QUEUE         Specify a message queue of an XMPP bridge to contact.
                        Defaults to /replies.
  --loglevel LOGLEVEL   Valid log levels: critical, error, warning, info,
                        debug, notset. Defaults to INFO.
  --message [MESSAGE [MESSAGE ...]]
                        Text message to send to the XMPP bridge.

If you want to redirect stdout or stderr from something else so this utility
can transmit it, make the last argument a - (per UNIX convention) to catch
them, like this: echo foo | send_message.py -
```
