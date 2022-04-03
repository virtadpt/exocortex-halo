
MOOF MOOF MOOF - I need to write an actual readme that explains how to set this up.  The following line is so I don't forget because I spent two days troubleshooting this mistake.

wallabag.html goes in /path/to/searx/searx/templates/oscar/result_templates/

In searx/searx/settings.yml the following settings are required, otherwise the `command.py` engine will throw a cryptic exception:
* `default_lang : ""`
* `prefer_configured_language: False`

