beta_fork is a microservice which implements a Markov brain-back end for chatterbots.  To put it another way, rather than develop multiple bots with multiple chat engine implementations and multiple databases backing them (which aren't easy to keep synchronized), the beta_fork server implements a simple REST API which bots make HTTP(S) requests against.  The bot is responsible for the client protocol in question (IRC, Slack, XMPP, whatever) while beta_fork accepts requests from the bots and generates responses.  The bots are responsible for deciding under what conditions they'll respond to text.  They are also responsible for deciding when they'll feed text to the Markov engine to train it a little more; for example, you could write a bot which takes a [WXR file](https://codex.wordpress.org/Tools_Export_Screen) from a blog and sends the text of every post to the Markov engine to train it.  This also means that the bots (and tools!) could be written in just about any programming language you like so long as it speaks HTTP(S) to communicate with the server.

A simple ACL (access control list) exists for the bots, consisting of whether or not it can read (get responses from) or write (add text to) the server.  The schema looks like this:

* botname - The name of the bot
* api_key - The bot's unique API key to access the server
* respond (Y/N) - Is the bot allowed to query the Markov engine so it can respond?
* learn (Y/N) - Is the bot allowed to train the Markov engine on what it sees?

An architecture like this also makes it possible to switch out the text recognition and discussion engines without needing to rewrite the bots that rely upon the microservice.  Right now I'm just using a Markov engine but there is no reason that I couldn't use something more sophisticated in the future.

One of the things you may wish to experiment with are writing bots that sit in the same communication channels as you (IRC, Slack), are configured to listen for everything you say preferentially, and always learn from what you say.

This is not going to be a full reimplementation of anyone, anytime soon.  It's a toy that seems like it'll be fun to experiment with and scratch a particular itch I'm feeling.  Plus, it's silly.

Modules that beta_fork relies upon:

* Cobe - https://github.com/pteichman/cobe
* BaseHTTPServer (included in Python by default)
* SQLite (included in Python by default)

The proof-of-concept IRC bot relies upon:

* IRC - https://pythonhosted.org/irc/

If these modules aren't available in your distribution as native packages, I advise installing them inside of a Python virtual environment so they don't stomp on your distro pacakges.  You can create one with the command `virtualenv env` and then activate it with the command `source env/bin/activate` which will pull in the necessary variables to put and access everything inside of the sandbox.  If you use the run.sh script, it'll activate the virtualenv for you.  It is safe to check the exocortex-halo/ repository out onto your server, cd into the beta_fork/ subdirectory, and build the virtualenv in there; that's how I do it on my servers.

The dependent modules are listed in requirements.txt, and can be installed to the sandbox (after activating it) with the command `pip install -r requirements.txt`

The REST API rails look like this:

* / - Online documentation. (GET)
* /ping - Ping the server to see if it's available.  Responds with "pong" (GET)
* /response - Given some JSON as input ({ "botname": "name", "apikey": "some API key", "stimulus": "Some text to respond to." }), run it through the chatbot brain and return a response.  Responses will take the form { "response": "Some response here...", "id": <HTTP response code> }  (GET)
* /learn - Given some JSON as input ({ "botname": "Alice", "apikey": "abcd", "stimulus": "This is some text I want to train the Markov engine on. I do not expect to get a response to the text at the same time." }), run it through the chatbot brain to train it a little more.  Does not return a linguistic response to the text, instead it responds with { "response": "trained", "id": <HTTP response code> }  (PUT)
* /register - Registers the API key of a new client bot with the server.  This isn't meant to be used by the client, but on the server-side with a shell script or a manual command to control which bots can and can't access the server (which keeps people from monkeying around with the chatbot brain).  The server's administrative API key is required for this - it's kept in the server's .conf file.  (PUT)  This API rail requires the following HTTP headers:
** X-API-Key - The server's management API key, which restrictg access.

The /register API rail requires a JSON document of the following form:

```
    {
        "name": "Name of bot",
        "api-key": "bot's unique API key",
        "respond": "Y/N",
        "learn": "Y/N"
    }
```

/register will return a JSON document that looks like one of the following:

```
    { "response": "success" }
```

or

```
    { "response": "failure" }
```

* /deregister - Deregisters the API key of an existing client/bot from the server.  This isn't meant to be used by the client, but on the server-side with a shell script or manual command.  The server's administrative API key is required for this - it's value is stored in the server's .conf file.  (PUT)

The /deregister API rail requires a JSON document of the following form:

```
    {
        "name": "Name of bot",
        "api-key": "bot's API key"
    }
```

/deregister will return a JSON document that looks like one of the following:

```
    { "response": "success" }
```

or

```
    { "response": "failure" }
```

