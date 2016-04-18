This is a relatively simple bot that is part of the Exocortex Halo (https://github.com/virtadpt/exocortex-halo) project which operates in concert with other bots to implement fire-and-forget web search requests.  My use case is this: While out and about without a laptop, use an XMPP client running on my phone to send a command of the form "<agent>, top twenty hits for <some weird search term>."  These commands are picked up by exocortex_xmpp_bridge.py and stored in an internal message queue that is periodically polled (by default, once a minute) by web_search_bot.py.

web_search_bot.py parses the JSON document to determine what kind of search request to make, assembles the search strings, and runs a couple of searches against a list of search engines configured in web_search_bot.conf.  I like to use privacy-preserving search engines so the list of stuff to filter out of the returned HTML (currently hardcoded in web_search_bot.py's hyperlinks_we_dont_want[] list) is specific to them.  One of the things I need to do is split that out into a configuration file to make it easier to maintain.

web_search_bot.py is also capable of e-mailing search terms to an address specified in the command.  For example, "<agent>, send you@example.com top twenty hits for <some weird search term>"

Requires BeautifulSoup4 (http://www.crummy.com/software/BeautifulSoup/) to parse the HTML returned by the search engines.  Try installing it from your distro's default package repositories - Arch Linux and Ubuntu v14.04 have it already so you don't need to set it up yourself.

web_search_bot.py currently only supports up to forty (40) search results.  Specifying an invalid number causes it to default to ten (10).

If you would like to add your own search engines to the list that web_search_bot draws from, the process is fairly simple: Get the URL with which you can specify a URL encoded search request (for example, https://startpage.com/do/search?q=).  Run a search against a search engine for something random (it doesn't need to be a specific search) to get a results page.  Extract all of the links from the returned HTML.  Sort through them to throw out all of the stuff that isn't a URL to a search result; for each thing you throw out, append it to the list *hyperlinks_we_dont_want* in the web_search_bot.conf file (or whatever you've named it if you're running multiple instances of the bot).  Here is some sample Python code (which I'll eventually turn into a utility to help with this process that I use to set up the example configuration file:

```
from bs4 import BeautifulSoup
from bs4 import SoupStrainer
import requests
request = requests.get('https://www.example.com/?q=fooble')
link_extractor = SoupStrainer('a')
html = BeautifulSoup(request.content, 'html.parser', parse_only=link_extractor)
links = html.find_all('a')
for i in links:
    hyperlink = i.get("href")
    if not hyperlink:
        continue
    print hyperlink.strip()
    print
```

