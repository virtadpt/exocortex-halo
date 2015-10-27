This is a relatively simple bot that is part of the Exocortex Halo (https://github.com/virtadpt/exocortex-halo) project which operates in concert with other bots to implement fire-and-forget web search requests.  My use case is this: While out and about without a laptop, use an XMPP client running on my phone to send a command of the form "<agent>, top twenty hits for <some weird search term>."  These commands are picked up by exocortex_xmpp_bridge.py and stored in an internal message queue that is periodically polled (by default, once a minute) by web_search_bot.py.

web_search_bot.py parses the JSON document to determine what kind of search request to make, assembles the search strings, and runs a couple of searches against a list of search engines configured in web_search_bot.conf.  I like to use privacy-preserving search engines so the list of stuff to filter out of the returned HTML (currently hardcoded in web_search_bot.py's hyperlinks_we_dont_want[] list) is specific to them.  One of the things I need to do is split that out into a configuration file to make it easier to maintain.

web_search_bot.py is also capable of e-mailing search terms to an address specified in the command.  For example, "<agent>, send you@example.com top twenty hits for <some weird search term>"

Requires BeautifulSoup4 (http://www.crummy.com/software/BeautifulSoup/) to parse the HTML returned by the search engines.  Try installing it from your distro's default package repositories - Arch Linux and Ubuntu v14.04 have it already so you don't need to set it up yourself.

web_search_bot.py currently only supports up to thirty (30) search results.  Specifying an invalid number causes it to default to ten (10).

