This is a basic microservice which attempts to solve the following problem:

I have a large-ish JSON document (like this: [https://github.com/iancoleman/cia_world_factbook_api](https://github.com/iancoleman/cia_world_factbook_api)).  I want to explore it in such a way that I don't have to copy-and-paste a lot of JSON into a text editor, prettify it, poke around in the keys for what I want, modify my query, and do this over and over again to explore the data and find [JSONpaths](https://support.smartbear.com/alertsite/docs/monitors/api/endpoint/jsonpath.html) for what I want.  I don't necessarily want to use a full database server for this, nor do I necessarily want to fight with converting and importing said JSON into the database.  I just want to poke around in the JSON natively.

I also wanted a universal tool for this, so I could conceivably throw any JSON dump at it and poke around in there.  Ultimately, my use case for this is making various kinds of databases and data sets available to my bots for processing, but this is also the sort of problem that I think a lot of people might have.  So, I made it as generic as possible.

This microservice requires no external dependencies, only a basic [Python 3](https://www.python.org/) install.  And, of course, a well-formed JSON document of some kind, like the aforementioned CIA World Factbook JSON dump.  No virtualenvs necessary.  No config files to mess around with.  Just a pure CLI (and systemd .service file, if that's how you roll).

Online help: `./universal_json_server.py --help`

```
usage: universal_json_server.py [-h] [--loglevel LOGLEVEL] [--host HOST]
                                [--port PORT] [--json JSON]

A microservice that takes an arbitrary JSON document (like a database or API
dump) and serves it up as a read-only REST API.

optional arguments:
  -h, --help           show this help message and exit
  --loglevel LOGLEVEL  Valid log levels: critical, error, warning, info,
                       debug, notset. Defaults to INFO.
  --host HOST          Local IP the server listens on. Defaults to 127.0.0.1
                       (all local IPs).
  --port PORT          Port the server listens on. Default 11000/tcp.
  --json JSON          Full path to the JSON document to serve.
```

A basic example: `./universal_json_server.py --loglevel debug --json ~/cia_world_factbook_api/data/factbook.json`

Access it with your favorite tool ([Huginn](https://github.com/huginn/huginn) bots, [cURL](https://curl.haxx.se/), whatever).
