
This is a handful of code for integrating the [Manticore search engine](https://manticoresearch.com) with [Wallabag](https://wallabag.org/), and then plugging Manticore into [Searx](https://github.com/searx/searx).  I built this because MySQL's built in search feature is incredibly slow when it comes to searching very large volumes of data in a single column, such as one's stored articles in Wallabag.

* README.md - You're soaking in it.
* manticore.conf.example - A basic configuration file for Manticore that can interface with and index a Wallabag install.
* searx-search_manticore.sh - Shell script that sends queries to `searchd`, parses the JSON returned, and emits search results, one per line on stdout for Searx to pick up.  Requires
    * [cURL](https://curl.se)
    * [jq](https://stedolan.github.io/jq/)
* searx-wallabag-configuration.yml - A snippet of YAML for [Searx](https://github.com/searx/searx)'s _settings.yml_ file that adds Manticore support.
* update-manticore-indexes.sh - My shell script for regenerating Manticore's indexes every time it runs.  I use it as a cronjob.
* wallabag.html - An HTML template file for Searx that displays Manticore!Wallabag search results.  Goes in _/path/to/searx/searx/templates/oscar/result_templates/_.

In _searx/searx/settings.yml_ the following settings are required, otherwise the `command.py` engine will throw a cryptic exception:
* `default_lang : ""`
* `prefer_configured_language: False`

