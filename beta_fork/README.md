beta_fork is a microservice which implements a Markov brain-back end for chatterbots.  To put it another way, rather than develop multiple bots with multiple chat engine implementations and multiple databases backing them (which aren't easy to keep synchronized), the beta_fork server implements a simple REST API which bots make HTTP(S) requests against.  The bot is responsible for the client protocol in question (IRC, Slack, XMPP, whatever) while beta_fork accepts requests from the bots, 

The bots are responsible for deciding under what conditions they'll respond to text.  They are also responsible for deciding when they'll feed text to the Markov engine to train it a little more.

An architecture like this also makes it possible to switch out the text recognition and discussion engines without needing to rewrite the bots that rely upon the microservice.  Right now I'm just using a Markov engine but there is no reason that I couldn't use something more sophisticated in the future.

Modules that beta_fork relies upon:

* Cobe - https://github.com/pteichman/cobe
* IRC - https://pythonhosted.org/irc/
* BaseHTTPServer (included in Python by default)

This is not going to be a full reimplementation of anyone, anytime soon.  It's a toy that seems like it'll be fun to experiment with and scratch a particular itch I'm feeling.  Plus, it's silly.

If these modules aren't available in your distribution as native packages, I advise inside of python virtual environments so they don't stomp on your distro pacakges.  You can create one with the command `virtualenv env` and then activate it with the command `source env/bin/activate` which will pull in the necessary variables to put and access everything inside of the sandbox.  It is safe to check the exocortex-halo/ repository out onto your server, cd into the beta_fork/ subdirectory, and build the virtualenv in there; that's how I do it.

The dependent modules are in requirements.txt, and can be installed to the sandbox (after activating it) with the command `pip install -r requirements.txt`

