beta_fork is a microservice which implements a Markov brain-back end for chatterbots.  To put it another way, rather than develop multiple bots with multiple chat engine implementations and multiple databases backing them (which aren't easy to keep synchronized), the beta_fork server implements a simple REST API which bots make HTTP(S) requests against.  The bot is responsible for the client protocol in question (IRC, Slack, XMPP, whatever) while beta_fork accepts requests from the bots and generates responses.  The bots are responsible for deciding under what conditions they'll respond to text.  They are also responsible for deciding when they'll feed text to the Markov engine to train it a little more.  This also means that the bots could be written in just about any programming language you like so long as it speaks HTTP(S) to communicate with the server.

A simple ACL (access control list) exists for the bots, consisting of whether or not it can read (get responses from) or write (add text to) the server.  The schema looks like this:

* botname
* api_key
* respond (Y/N)
* learn (Y/N)

An architecture like this also makes it possible to switch out the text recognition and discussion engines without needing to rewrite the bots that rely upon the microservice.  Right now I'm just using a Markov engine but there is no reason that I couldn't use something more sophisticated in the future.

Modules that beta_fork relies upon:

* Cobe - https://github.com/pteichman/cobe
* BaseHTTPServer (included in Python by default)
* SQLite (included in Python by default)

The proof-of-concept IRC bot relies upon:

* IRC - https://pythonhosted.org/irc/

This is not going to be a full reimplementation of anyone, anytime soon.  It's a toy that seems like it'll be fun to experiment with and scratch a particular itch I'm feeling.  Plus, it's silly.

If these modules aren't available in your distribution as native packages, I advise inside of python virtual environments so they don't stomp on your distro pacakges.  You can create one with the command `virtualenv env` and then activate it with the command `source env/bin/activate` which will pull in the necessary variables to put and access everything inside of the sandbox.  It is safe to check the exocortex-halo/ repository out onto your server, cd into the beta_fork/ subdirectory, and build the virtualenv in there; that's how I do it.

The dependent modules are in requirements.txt, and can be installed to the sandbox (after activating it) with the command `pip install -r requirements.txt`

The REST API rails look like this:

* / - Online documentation. (GET)
* /ping - Ping the server to see if it's available.  Responds with "pong" (GET)
* /response - Given some JSON as input ({ "botname": "name", "apikey": "some API key", "stimulus": "Some text to respond to." }), run it through the chatbot brain and return a response.  Responses will take the form { "response": "Some response here...", "id": <HTTP response code> }  (GET)
** X-API-Key - The bot's unique API key to prevent abuse.
** X-Text-To-Respond-To - Text to run through the chatbot brain.  It would be ideal if the text was cleaned up (extraneous whitespace stripped out, only one sentence at a time) but just in case some cleanup will be done on the server side also.
* /learn - Given a string of input, run it through the chatbot brain to train ita little more.  Does not return a response to the text, instead it responds with { "response": "trained" }  (PUT)  Requires the following HTTP headers:
** X-API-Key - The bot's unique API key to prevent abuse.
** X-Text-To-Learn - Text to run through the chatbot brain.  It would be ideal if the text was cleaned up (extraneous whitespace stripped out, only one sentence at a time) but just in case some cleanup will be done on the server side also.
* /register - Registers the API key of a new client with the server.  This isn't meant to be used by the client, but on the server-side with a shell script to control what bots can and can't access the server (which keeps people from monkeying around with the chatbot brain).  An API key is required for this, also - it's kept in the server's .conf file.  (PUT)  Requires the following HTTP headers:
** X-API-Key - The server's API key, restricting access.

The /register API rail requires a JSON document of the following form:

```
    {
        "name": "Name of bot",
        "api-key": "bot's API key",
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

* /deregister - Deregisters the API key of an existing client from the server.  This isn't meant to be used by the client, but on the server-side with a shell script.  An API key is required for this, also - it's kept in the server's .conf file.  (PUT)  Requires the following HTTP headers:
** api-key - The server's API key, restricting access.

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

