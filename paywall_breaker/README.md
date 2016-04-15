paywall_breaker.py

This construct is part of the Exocortex Halo (https://github.com/virtadpt/exocortex-halo) and is designed to jump paywalls so that articles can be read.  The process reads like this:

* Paywall Breaker listens for requests in a message queue.
* The construct extracts a URL sent by its designated user.
* If the URL is valid, the construct randomly picks the user-agent of a search engine's indexing spider from a list and pretends to be that spider.
* The construct downloads the HTML page.
* Beautiful Soup is used to parse the HTML and extract the
    * <title>
    * <body>
* The construct pings an instance of Etherpad-Lite and allocates a new pad.
* The extracted text is copied into the new pad and saved.
* The construct then e-mails its user with a link to the new pad (or an error message).

Requirements above and beyond what Python usually packages:

* Requests
* Beautiful Soup v4
    * It is preferable that you install the version native to your distribution of Linux, but if need be you can install it with pip).
* Python Etherpad-Lite (https://github.com/Changaco/python-etherpad_lite)
* Validators (https://validators.readthedocs.org/en/latest/)
    * Used to validate the correctness of URLs.
* A running copy of Etherpad-Lite that it can securely contact.  If it's running on the same host, so much the better.

I recommend allocating a virtualenv to put everything in.  It's kind of annoying that pre-installed Python modules don't get pulled into virtualenvs when they're constructed, but you can't always have chocolate fudge/mint cookies, either.

Commands from the user look like this:

```
Paywall Breaker, get https://www.example.com/paywalled_article.html
```

You can run multiple copies of Paywall Breaker in the same exocortex so long as they all have different names.  Don't forget that they'll need separate message queues, also.
