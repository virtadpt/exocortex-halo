I originally wrote this utility as a way to catch the output of a script running on a server that I can't set up SMTP on, but upon reflection it would also be useful for sending notifications at arbitrary times (say, when someone logs into an account it's executed by their ~/.bashrc script, or with cron as a watchdog).

The requirements for this utility are modest - the only module not included in the basic Python 2 installation is Requests, and that's usually available as a package in your distro's repository.

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
