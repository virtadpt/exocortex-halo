paywall_breaker.py

This construct is part of the Exocortex Halo (https://github.com/virtadpt/exocortex-halo) and is designed to jump paywalls so that articles can be read.  The process reads like this:

* Paywall Breaker listens for requests in a message queue.
* The construct extracts a URL sent by its designated user.
* If the URL is valid, the construct randomly picks the user-agent of a search engine's indexing spider from a list and pretends to be that spider.
* The construct downloads the HTML page.
* Beautiful Soup is used to parse the HTML and extract the
    * <title>
    * <head>
    * <body>
* The construct pings an instance of Etherpad-Lite and allocates a new pad.
* The extracted text is copied into the new pad and saved.
* The construct then e-mails its user with a link to the new pad (or an error message).

Requirements above and beyond what Python usually packages:

* Requests
* Beautiful Soup v4
* Python Etherpad-Lite (https://github.com/Changaco/python-etherpad_lite)
* A running copy of Etherpad-Lite that it can securely contact.

Commands from the user look like this:

```
Paywall Breaker, get https://www.example.com/paywalled_article.html
```


