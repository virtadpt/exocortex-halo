This is an IRC bot which incorporates two major functions: First, it's designed to ride alongside you on IRC, watching what you say and learning from it (within certain limits - it looks for relatively long words and sentences) so that it can occasionally answer for you (eventually, when addressed directly it will try to answer as you) (it will, to a lesser extent, learn from others in the channel to become a more complete conversationalist), and it will eventually ghost as you, which is to say it can sit in channels and monitor for certain people or terms, and let you speak through the bot like a limited IRC client (I haven't yet figured out how to implement the UI of this bit).

Requires the IRC module for Python 2 (https://pythonhosted.org/irc/) and halpy, a re-implementation of the MegaHAL engine as a Python module (https://code.google.com/p/halpy/).

This is not going to be a full reimplementation of anyone, anytime soon.  It's a toy that seems like it'll be fun to experiment with and scratch a particular itch I'm feeling.

