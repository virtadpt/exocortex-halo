This is an IRC bot which carries out two major functions: First, it's designed to ride alongside you on IRC, watching what you say and learning from it (within certain limits - it looks for relatively long words and sentences) so that it can occasionally answer for you (eventually, when addressed directly it will try to answer as you) (it will, to a lesser extent, learn from others in the channel to become a more complete conversationalist), and it will eventually ghost as you, which is to say it can sit in channels and monitor for certain people or terms, and let you speak through the bot like a limited IRC client (I haven't yet figured out how to implement the UI of this bit).  I named the bot the Dixie Flatline (http://everything2.com/title/Dixie+Flatline) because the idea of an IRC bot that follows you around and learns how to respond like you amuses me greatly.

Requires the IRC module for Python (https://pythonhosted.org/irc/) and Cobe, a pretty awesome re-implementation of the MegaHAL engine in Python (https://github.com/pteichman/cobe) with some pretty nifty features (that saved me a lot of time.

This is not going to be a full reimplementation of anyone, anytime soon.  It's a toy that seems like it'll be fun to experiment with and scratch a particular itch I'm feeling.  Plus, it's silly.

If these modules aren't available in your distribution as native packages, I advise setting them up inside of python virtual environments so they don't stomp on your distro pacakges.  You can set one up with the command `virtualenv env` and then activate it with the command `source env/bin/activate` which will pull in the necessary variables to put and access everything inside of the sandbox.  It is safe to check the exocortex-halo/ repository out onto your server, cd into the bot's directory, and allocate the virtualenv in there; that's how I do it.

The two dependent modules are in requirements.txt, and can be installed to the sandbox (after activating it) with the command `pip install -r requirements.txt`

Remember that the virtualenv has to be pulled in before the bot will run.  I included a script `run.sh` which does this automagickally for you; it will also pass any command line arguments to the bot (like --help).

