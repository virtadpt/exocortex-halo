Please note that the less well curated your media collection is, the more trouble the bot will have interacting with it.  At the very least make sure that your media metadata is not fallacious (such as Folk Music mislabled as Talk Radio).

#The Command Parser
The command parser for this bot is very different from the other ones I've written.  It uses a parser that draws from [NLP](https://en.wikipedia.org/wiki/Natural_language_processing) techniques as well as [fuzzy matching](https://en.wikipedia.org/wiki/Fuzzy_matching_(computer-assisted_translation] using a module called [Fuzzywuzzy](https://github.com/seatgeek/fuzzywuzzy).  This means that the command parser needs to be front-loaded with sample text to train it.  I've included a directory of [sample corpora](https://en.wikipedia.org/wiki/Text_corpus) in the subdirectory *corpora/*.  Each file contains text which corresponds to a particular kind of question or command you can send the bot, such as "Do I have Johnny Mnemonic in my video library?" or "Play everything in my library by Information Society."

The name of each file corresponds to the type of interaction to parse: A search or a command.  For example, *corpora/search_requests_genres.txt* is used to teach the parser how to recognize when the user is asking the bot to search the genres (media metadata, like ID3 tags).  You can and should update these files with text that is more idiosyncratic of how you would ask questions and give commands to Kodi as if it had a verbal command interface.  All of these files must be present, but if a function is not used on your install (say, music playback on a set-top box) it should be of length 0.  I also plan on adding a list of disabled command classes in the configuration file.

Recognized filenames and corresponding functions:

* search_requests_genres.txt - Questions pertaining to searching your media library by genre.
* search_requests_artists.txt - Questions pertaining to searching your media library by artist or musician.
* search_requests_albums.txt - Questions pertaining to searching your media library by title of album or collection.
* search_requests_songs.txt - Questions pertaining to searching your media library by title of song or track.
* search_requests_videos.txt - Questions pertaining to searching your media library by title of video, movie, or show.
* commands_play.txt - Commands pertaining to starting playback of media.
* commands_pause.txt - Commands pertaining to pausing playback of media.
* commands_stop.txt - Commands pertaining to halting playback of media.
* commands_forward.txt - Commands pertaining to skipping forward.
* commands_backward.txt - Commands pertaining to skipping backward.
* commands_shuffle.txt - Commands pertaining to shuffling through your music library.  This is where party mode happens.
* help_basic.txt - Basic questions for getting online help.
* help_audio.txt - Questions for getting online help for audio.
* help_video.txt - Questions for getting online help for video.
* help_commands.txt - Questions for getting online help for other commands.

If the bot isn't quite sure if it's got a good match, it'll tell you so.  By default, kodi_bot.py will consider any confidence metric over 25% a good match.  You can change this by editing the configuration file and restarting the bot.

To make this bot work reliably, you'll probably have to create an *advancedsettings.xml* file in the Kodi *userdirectory/* directory on your Kodi box, per [these instructions](https://kodi.wiki/view/Advancedsettings.xml).  At least in part, the contents of this file should look something like this:

```
<advancedsettings>
    <network>
        <curlclienttimeout>120</curlclienttimeout>
    </network>
</advancedsettings>
```

Then restart Kodi.  I've found that this modification makes it much easier for the bot to generate a media library.  Why doesn't Kodi have an API to do this?  I don't know.

Please note that if you have any filenames with broken character encodings, Python will not be able to decode the bytestring and will barf.  By "broken" I mean filenames that look like this: **The.X-Files.S09E03.D'$'\346''monicus.WEBRip.x264-FUM.mp4**