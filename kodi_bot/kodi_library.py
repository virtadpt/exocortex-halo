#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# kodi_library.py - Kodi Bot module which does the heavy lifting of acquiring,
#   organizing, and manipulating a media library from Kodi.  Kodi doesn't offer
#   any of this functionality so we have to do it ourselves.

# By: The Doctor <drwho at virtadpt dot net>
#       0x807B17C1 / 7960 1CDC 85C9 0B63 8D9F  DD89 3BD8 FF2B 807B 17C1

# License: GPLv3

# v2.1 - Added functions to pause, unpause, and stop whatever's playing.
#         - Added ability to ping the Kodi JSON RPC server.
#         - Renamed is_currently_playing() to _is_currently_playing() so that
#            it looks like what it's supposed to be, i.e., a helper function.
#         - Added helper function _clear_current_playlist() to clear the
#           default playlist of entries.  This is something Kodi forces you to
#           do when you change what you want to play.
# v2.0 - Removed kodipydent, replaced with raw HTTP requests using Requests.
# v1.0 - Initial release.

# TO-DO:
# - Refactor all of the "make HTTP requests and check the result" code into a
#   separate helper function.
# - Split the functions that don't actually build the media library but instead
#   interact with it into a separate module.
# - Split the repeated code that builds the payload{} hash over and over into
#   a helper function to make maintenance easier.  Customization can always
#   be done at the function level, and that usually takes the form of adding a
#   params{} sub-hash.

# Load modules.
import json
import logging
import os
import requests

from fuzzywuzzy import fuzz

# Global defaults.
# In Kodi, the currently playing media is always in playlist #1.
default_playlist = 1

# Global variables.
# JSON RPC payload template to send to the server.
payload = {}
payload["jsonrpc"] = "2.0"
payload["method"] = ""
payload["id"] = 1

# Functions.

# get_media_sources(): Generate a list of media sources on the Kodi box.  From
#   the Kodi docs, there are only two we have to care about, video and music.
#   I'm using the canonical Kodi names for consistency's sake.  Takes three
#   arguments, a Kodi URL, an HTTP Basic Auth object, and a hash of customer
#   headers.  Returns a hash table containing the media sources the Kodi box
#   has configured.
def get_media_sources(kodi_url, kodi_auth, headers):
    logging.debug("Entered media_library.get_media_sources().")

    sources = {}
    sources["video"] = []
    sources["music"] = []
    request = None
    tmp = None

    # Build a command to POST to Kodi.
    command = {}
    command["id"] = 1
    command["jsonrpc"] = "2.0"
    command["method"] = "Files.GetSources"
    command["params"] = {}

    # Build a list of video sources on the Kodi box.
    command["params"]["media"] = "video"
    request = requests.post(kodi_url, auth=kodi_auth, headers=headers,
        data=json.dumps(command))
    tmp = request.json()
    if "sources" not in tmp["result"]:
        logging.warn("'video' is not a registered media source.")
    else:
        for i in tmp["result"]["sources"]:
            sources["video"].append(i["file"])

    # Build a list of music sources on the Kodi box.
    command["params"]["media"] = "music"
    request = requests.post(kodi_url, auth=kodi_auth, headers=headers,
        data=json.dumps(command))
    tmp = request.json()
    if "sources" not in tmp["result"]:
        logging.warn("'music' is not a registered media source.")
    else:
        for i in tmp["result"]["sources"]:
            sources["music"].append(i["file"])

    logging.debug("Known media sources: %s" % str(sources))
    return sources

# build_media_library(): Function that builds the local media library, because
#   there's no straightforward way to query Kodi.  Takes five args, a Kodi URL,
#   an HTTP Basic Auth object, a hash of custom headers, a hash table of media
#   sources, and a list of directories to ignore.  Returns a new copy of the
#   media library.
def build_media_library(kodi_url, kodi_auth, headers, sources, exclude_dirs):
    logging.debug("entered kodi_library.build_media_library().")
    logging.info("Now indexing media library... this could take a while.")

    request = None
    tmp = None

    # Set up categories in the media library.
    media_library = {}
    media_library["artists"] = []
    media_library["albums"] = []
    media_library["audio"] = []
    media_library["movies"] = []
    media_library["music"] = []
    media_library["musicvideos"] = []
    media_library["songs"] = []
    media_library["tv"] = []
    media_library["video"] = []

    # Build a command to POST to Kodi.
    command = {}
    command["id"] = 1
    command["jsonrpc"] = "2.0"
    command["method"] = "Files.GetDirectory"
    command["params"] = {}
    command["params"]["media"] = "files"
    command["params"]["directory"] = ""

    # For every media source...
    for source in list(sources.keys()):
        # For every directory in every media source...
        for directory in sources[source]:
            logging.debug("Now scanning media directory %s..." % directory)

            # Skip the EXT?fs lost+found directory.
            if directory.endswith("lost+found/"):
                continue

            # Check the list of directories to skip.
            bounce = False
            for x in exclude_dirs:
                if bounce:
                    logging.debug("Sorry - gotta bounce!")
                    break
                if x in directory:
                    logging.debug("Skipping over excluded directory %s." % directory)
                    bounce = True
                    break
            if bounce:
                logging.debug("Nope - skipping this directory!")
                continue

            # Get the contents of the directory.
            command["params"]["directory"] = directory
            request = requests.post(kodi_url, auth=kodi_auth,
                data=json.dumps(command), headers=headers)
            tmp = request.json()

            # Catch file system errors, like file permissions.
            if "error" in list(tmp.keys()):
                logging.warn("Got one of Kodi's 'Invalid params' error messages when accessing %s.  Might be bad permissions.  Skipping." % directory)
                continue

            # Catch the "no files in directory" case.
            if tmp["result"]["limits"]["start"] == 0:
                if tmp["result"]["limits"]["end"] == 0:
                    logging.warn("Found empty directory %s, skipping." % directory)
                    continue
            # "Explicit is better than implicit."

            tmp = tmp["result"]["files"]
            # For every thing in that directory...
            for k in tmp:
                # If you run into a subdirectory, append it to the list of
                # sources so it can also be scanned.  There is undoubtedly a
                # better and more stable way of doing this but I don't know
                # what it is yet.
                if k["filetype"] == "directory":
                    logging.debug("Found subdirectory %s in the media library.  Adding it to the queue to index later." % k["file"])
                    sources[source].append(k["file"])
                    continue

                # Otherwise, add the media to the library.
                media_tmp = {}
                media_tmp["file"] = k["file"]
                media_tmp["label"] = k["label"]
                media_library[source].append(media_tmp)

    return media_library

# get_artists(): Gets the directory of artists from the Kodi media database.
#   Takes three arguments, a Kodi URL, an HTTP Basic Auth object, and a hash
#   of custom headers.  Returns an array of artists.
def get_artists(kodi_url, kodi_auth, headers):
    logging.debug("Entered kodi_library.get_artists().")
    request = None
    artists = None
    list_of_artists = []

    # Build a command to POST to Kodi.
    command = {}
    command["id"] = 1
    command["jsonrpc"] = "2.0"
    command["method"] = "AudioLibrary.GetArtists"

    request = requests.post(kodi_url, auth=kodi_auth, data=json.dumps(command),
        headers=headers)
    artists = request.json()

    if "artists" not in artists["result"]:
        logging.warn("No artists found in library.")
        return None

    for i in artists["result"]["artists"]:
        tmp = {}
        tmp["artistid"] = i["artistid"]
        tmp["artist"] = i["artist"]
        list_of_artists.append(tmp)

    return list_of_artists

# get_albums(): Gets the directory of albums from the Kodi media database.
#   Takes three arguments, a Kodi URL, an HTTP Basic Auth object, and a hash
#   of custom headers.  Returns an array of albums.
def get_albums(kodi_url, kodi_auth, headers):
    logging.debug("Entered kodi_library.get_albums().")
    request = None
    albums = None
    list_of_albums = []

    # Build a command to POST to Kodi.
    command = {}
    command["id"] = 1
    command["jsonrpc"] = "2.0"
    command["method"] = "AudioLibrary.GetAlbums"

    request = requests.post(kodi_url, auth=kodi_auth, data=json.dumps(command),
        headers=headers)
    albums = request.json()

    if "albums" not in albums["result"]:
        logging.warn("No albums found in library.")
        return None

    for i in albums["result"]["albums"]:
        tmp = {}
        tmp["albumid"] = i["albumid"]
        tmp["label"] = i["label"]
        list_of_albums.append(tmp)
    return list_of_albums

# get_songs(): Gets the directory of songs from the Kodi media database.
#   Takes Takes three arguments, a Kodi URL, an HTTP Basic Auth object, and a
#   hash of custom headers.  Returns an array of songs.
def get_songs(kodi_url, kodi_auth, headers):
    logging.debug("Entered kodi_library.get_songs().")
    request = None
    songs = None
    list_of_songs = []

    # Build a command to POST to Kodi.
    command = {}
    command["id"] = 1
    command["jsonrpc"] = "2.0"
    command["method"] = "AudioLibrary.GetSongs"

    request = requests.post(kodi_url, auth=kodi_auth, data=json.dumps(command),
        headers=headers)
    songs = request.json()

    if "songs" not in songs["result"]:
        logging.warn("No songs found in library.")
        return None

    for i in songs["result"]["songs"]:
        tmp = {}
        tmp["songid"] = i["songid"]
        tmp["label"] = i["label"]
        list_of_songs.append(tmp)

    return list_of_songs

# get_movies(): Gets the directory of movies from the Kodi media database.
#   Takes Takes three arguments, a Kodi URL, an HTTP Basic Auth object, and a
#   hash of custom headers.  Returns an array of movies.
def get_movies(kodi_url, kodi_auth, headers):
    logging.debug("Entered kodi_library.get_movies().")
    request = None
    movies = None
    list_of_movies = []

    # Build a command to POST to Kodi.
    command = {}
    command["id"] = 1
    command["jsonrpc"] = "2.0"
    command["method"] = "VideoLibrary.GetMovies"

    request = requests.post(kodi_url, auth=kodi_auth, data=json.dumps(command),
        headers=headers)
    movies = request.json()

    if "movie" not in movies["result"]:
        logging.warn("No movies found in library.")
        return None

    for i in movies["result"]["movies"]:
        tmp = {}
        tmp["movieid"] = i["movieid"]
        tmp["label"] = i["label"]
        list_of_movies.append(tmp)

    return list_of_movies

# get_tv_shows(): Gets the directory of movies from the Kodi media database.
#   Takes three arguments, a Kodi URL, an HTTP Basic Auth object, and a hash
#   of custom headers.  Returns an array of TV shows.
def get_tv_shows(kodi_url, kodi_auth, headers):
    logging.debug("Entered kodi_library.get_tv_shows().")
    request = None
    tv = None
    list_of_tv_shows = []

    # Build a command to POST to Kodi.
    command = {}
    command["id"] = 1
    command["jsonrpc"] = "2.0"
    command["method"] = "VideoLibrary.GetTVShows"

    request = requests.post(kodi_url, auth=kodi_auth, data=json.dumps(command),
        headers=headers)
    tv = request.json()

    if "tv" not in tv["result"]:
        logging.warn("No television shows found in library.")
        return None

    for i in tv["result"]["tv"]:
        tmp = {}
        tmp["tvid"] = i["tvid"]
        tmp["label"] = i["label"]
        list_of_tv_shows.append(tmp)
    return list_of_tv_shows

# get_audio_genres(): Gets the directory of genres of audio media from the
#   Kodi media database.  Takes three arguments, a Kodi URL, an HTTP Basic Auth
#   object, and a hash of custom headers.  Returns an array of genres and genre
#   ID codes.  Why this isn't part of the media library itself, I don't know.
def get_audio_genres(kodi_url, kodi_auth, headers):
    logging.debug("Entered kodi_library.get_audio_genres().")
    request = None
    genres = None
    list_of_genres = []

    # Build a command to POST to Kodi.
    command = {}
    command["id"] = 1
    command["jsonrpc"] = "2.0"
    command["method"] = "AudioLibrary.GetGenres"

    request = requests.post(kodi_url, auth=kodi_auth, data=json.dumps(command),
        headers=headers)
    genres = request.json()

    if "genres" not in genres["result"]:
        logging.warn("No audio genres found in library.")
        return None

    for i in genres["result"]["genres"]:
        tmp = {}
        tmp["genreid"] = i["genreid"]
        tmp["label"] = i["label"]
        list_of_genres.append(tmp)
    return list_of_genres

# get_video_genres(): Gets the directory of genres of video media from the
#   Kodi media database.  Takes three arguments, a Kodi URL, an HTTP Basic Auth
#   object, and a hash of custom headers.  Returns an array of genres and genre
#   ID codes.
def get_video_genres(kodi_url, kodi_auth, headers):
    logging.debug("Entered kodi_library.get_video_genres().")
    request = None
    genres = None
    list_of_genres = []

    # Build a command to POST to Kodi.
    command = {}
    command["id"] = 1
    command["jsonrpc"] = "2.0"
    command["method"] = "VideoLibrary.GetGenres"
    command["params"] = {}
    command["params"]["type"] = ""

    # There are three possible values for "type": "movie," "tvshow," and
    # "musicvideo."
    # https://github.com/xbmc/xbmc/blob/4ad0edc3eba3d5022e20fb8713b1512d0e2210e4/xbmc/interfaces/json-rpc/schema/methods.json#L1456
    types = [ "movie", "tvshow", "musicvideo" ]

    for type in types:
        command["params"]["type"] = type
        request = requests.post(kodi_url, auth=kodi_auth,
            data=json.dumps(command), headers=headers)
        genres = request.json()

        if "genres" not in genres["result"]:
            logging.warn("Video genre %s not found in library." % type)
            continue

        for i in genres["result"]["genres"]:
            tmp = {}
            tmp["genreid"] = i["genreid"]
            tmp["label"] = i["label"]
            list_of_genres.append(tmp)

    return list_of_genres

# search_media_library_albums(): Takes a search term, a reference into a
#   section of the media library, and a minimum confidence and scans for
#   matches.  Returns a hash table containing the media's internal entry.
def search_media_library_albums(search_term, media_library, confidence):
    logging.debug("Entered kodi_library.search_media_library_albums.")

    match = 0
    result = {}
    result["confidence"] = 0
    result["label"] = ""

    for i in media_library:
        match = fuzz.token_sort_ratio(search_term.lower(), i["label"].lower())
        if match >= confidence and match > result["confidence"]:
            logging.debug("Replacing match with one of a higher confidence.")
            result["albumid"] = i["albumid"]
            result["label"] = i["label"]
            result["confidence"] = match

        # Short-circuit the search if we find a perfect match.
        if result["confidence"] == 100:
            logging.debug("Hot dog - perfect match!")
            tmp = []
            tmp.append(result)
            result = tmp
            break

    logging.debug("Value of result: %s" % str(result))
    return result

# search_media_library_artists(): Takes a search term, a reference into a
#   section of the media library, and a minimum match confidence and scans for
#   matches.  Returns a hash table containing the media's internal entry.  This
#   is a separate function because the "artists" part of the media library
#   doesn't use "label" as a key, so there's no good way of doing it
#   generically.
def search_media_library_artists(search_term, media_library, confidence):
    logging.debug("Entered kodi_library.search_media_library_artists.")

    match = 0
    result = {}
    result["confidence"] = 0
    result["artist"] = ""

    for i in media_library:
        match = fuzz.token_sort_ratio(search_term.lower(), i["artist"].lower())
        if match > result["confidence"]:
            logging.debug("Replacing match with one of a higher confidence.")
            result["artistid"] = i["artistid"]
            result["artist"] = i["artist"]
            result["confidence"] = match

        # Short-circuit the search if we find a perfect match.
        if result["confidence"] == 100:
            logging.debug("Hot dog - perfect match!")
            break

    tmp = []
    tmp.append(result)
    result = tmp
    logging.debug("Value of result: %s" % str(result))
    return result

# search_media_library_genres(): Takes a search term, a reference into a
#   section of the media library, and the minimum confidence in the match and
#   scans for matches.  Returns an array containing matching genres and
#   genre ID codes because it's quite common to have the same genre represented
#   with different equivalent spellings, because nobody uses the official list
#   of ID3 genre codes (https://en.wikipedia.org/wiki/List_of_ID3v1_Genres).
def search_media_library_genres(search_term, media_library, confidence):
    logging.debug("Entered kodi_library.search_media_library_genres.")
    logging.debug("My minimum match confidence metric is %d." % confidence)

    match = 0
    result = []

    for i in media_library:
        match = fuzz.token_set_ratio(search_term.lower(), i["label"].lower())
        if match >= confidence:
            logging.debug("Found a fairly decent genre match for %s: %s" % (search_term, i["label"]))
            tmp = {}
            tmp["label"] = i["label"]
            tmp["genreid"] = i["genreid"]
            result.append(tmp)

    logging.debug("It looks like I got %d possible matches for the genre %s." % (len(result), search_term))
    return result

# search_media_library_songs(): Takes a search term, a reference into a
#   section of the media library, and the minimum confidence in the match and
#   scans for matches.  Returns a sorted array containing matching song titles
#   and song ID codes because it's possible to have duplicates as well as
#   multiple different yet valid matches (such as chapters of an audiobook).
def search_media_library_songs(search_term, media_library, confidence):
    logging.debug("Entered kodi_library.search_media_library_songs.")

    match = 0
    result = []

    for i in media_library:
        match = fuzz.token_set_ratio(search_term.lower(), i["label"].lower())
        if match > confidence:
            logging.debug("Found a fairly decent track title match for %s with a confidence metric of %d: %s" % (search_term, match, i["label"]))
            tmp = {}
            tmp["label"] = i["label"]
            tmp["songid"] = i["songid"]
            result.append(tmp)

        if match == 100:
            logging.debug("Hot dog - perfect match!")

    logging.debug("It looks like I got %d possible matches for the song %s." % (len(result), search_term))
    logging.debug("Search results: %s" % str(result))
    return sorted(result)

# search_media_library_music(): Takes a search term, a reference into a
#   section of the media library, and the minimum confidence in the match and
#   scans for matches.  Returns a sorted array containing matching song titles
#   and filenames (with full paths) because Kodi treats "songs" and "music" as
#   two different things.  I got nothin'.
def search_media_library_music(search_term, media_library, confidence):
    logging.debug("Entered kodi_library.search_media_library_music.")

    match = 0
    result = []

    for i in media_library:
        match = fuzz.token_set_ratio(search_term.lower(), i["label"].lower())
        if match > confidence:
            logging.debug("Found a fairly decent track title match for %s with a confidence metric of %d: %s" % (search_term, match, i["label"]))
            tmp = {}
            tmp["label"] = i["label"]
            tmp["file"] = i["file"]
            result.append(tmp)

        if match == 100:
            logging.debug("Hot dog - perfect match!")

    logging.debug("It looks like I got %d possible matches for the song %s." % (len(result), search_term))
    return sorted(result)

# search_media_library_video(): Takes a search term, a reference into a
#   section of the media library, and the minimum confidence in the match and
#   scans for matches.  Returns a sorted array containing matching titles and
#   filenames (with full paths).
def search_media_library_video(search_term, media_library, confidence):
    logging.debug("Entered kodi_library.search_media_library_video.")

    match = 0
    result = []

    for i in media_library:
        match = fuzz.token_set_ratio(search_term.lower(), i["label"].lower())
        if match > confidence:
            logging.debug("Found a fairly decent track title match for %s with a confidence metric of %d: %s" % (search_term, match, i["label"]))
            tmp = {}
            tmp["label"] = i["label"]
            tmp["file"] = i["file"]
            result.append(tmp)

        if match == 100:
            logging.debug("Hot dog - perfect match!")

    logging.debug("It looks like I got %d possible matches for the video file %s." % (len(result), search_term))
    return sorted(result)

# _is_currently_playing: Function that queries which media playback system
#   is currently running, if any.  If media is currently playing or paused, you
#   will get an affirmative response, in the form of a JSON document saying
#   which player it is.  If no media is playing (stopped), you'll get an empty
#   array.  Takes three arguments, the Kodi JSON RPC URL, an HTTP
#   Basic Auth object, and a hash of headers.  Returns the output from Kodi to
#   be parsed and used elsewhere or None if there's an error.  The output
#   looks like this:
#   {
#
#
#
#   }
def _is_currently_playing(kodi_url, kodi_auth, headers):
    logging.debug("Entered kodi_library._is_currently_playing().")

    request = None
    result = {}

    # Set up the payload.
    payload = {}
    payload["jsonrpc"] = "2.0"
    payload["id"] = 1
    payload["method"] = "Player.GetActivePlayers"

    # Find out what, if anything is playing right now.
    try:
        request = requests.post(kodi_url, auth=kodi_auth, headers=headers,
            data=json.dumps(payload))
        result = json.loads(request.text)
        result = result["result"]
        logging.debug("Response from Kodi: %s" % str(result))
    except:
        logging.warn("Failed to get response from Kodi!")
        return None
    return result

# _get_song_title: Helper function that queries the media database by song ID
#   and returns the title.  Takes four arguments, the Kodi JSON RPC URL, an
#   HTTP Basic Auth object, a hash of headers, and the song ID.  Returns a
#   string on success or "None" if not.
def _get_song_title(kodi_url, kodi_auth, headers, songid):
    logging.debug("Entered kodi_library._get_song_title().")

    request = None
    result = {}

    # Set up the payload.
    payload = {}
    payload["jsonrpc"] = "2.0"
    payload["id"] = 1
    payload["method"] = "AudioLibrary.GetSongDetails"
    payload["params"] = {}
    payload["params"]["songid"] = songid

    # Query the title of the song from Kodi.
    try:
        request = requests.post(kodi_url, auth=kodi_auth, headers=headers,
            data=json.dumps(payload))
        result = json.loads(request.text)
        result = result["result"]["songdetails"]["label"]
        logging.debug("Response from Kodi: %s" % str(result))
    except:
        logging.warn("Failed to get response from Kodi!")
        return "Unknown"
    return result

# whats_playing: Function that queries Kodi to find out what's playing.
#   Takes three arguments, the Kodi JSON RPC URL, an HTTP Basic Auth object,
#   and a hash of headers.  Returns some information about what's playing right
#   now or "Nothing."
def whats_playing(kodi_url, kodi_auth, headers):
    logging.debug("Entered kodi_library.whats_playing().")

    is_playing = []
    request = None
    result = {}
    media_information = ""
    song_information = ""
    video_information = ""

    # Find out if anything is playing.
    is_playing = _is_currently_playing(kodi_url, kodi_auth, headers)
    if not is_playing:
        logging.debug("Nothing is playing at this time.")
        return "Nothing is playing at this time."
    is_playing = is_playing[0]
    logging.debug("Value of is_playing: %s" % str(is_playing))

    # Set up the payload.
    payload = {}
    payload["jsonrpc"] = "2.0"
    payload["id"] = 1
    payload["method"] = "Player.GetItem"
    payload["params"] = {}
    payload["params"]["playerid"] = is_playing["playerid"]

    try:
        request = requests.post(kodi_url, auth=kodi_auth, headers=headers,
            data=json.dumps(payload))
        result = json.loads(request.text)
        result = result["result"]["item"]
        logging.debug("Response from Kodi: %s" % str(result))
    except:
        logging.warn("Failed to get response from Kodi!")
        return "Nothing seems to be playing."

    # Parse the output from Kodi.
    media_information = "Now playing: "
    if result["type"] == "song":
        media_information = media_information + "The song " + result["label"] + " by "
        song_information = _get_song_title(kodi_url, kodi_auth, headers,
            result["id"])
    #if result["type"] == "video":
    return media_information

# pause_media: If something is playing, pause it.  Takes three arguments, the
#   Kodi JSON RPC URL, an HTTP Basic Auth object, and a hash of headers.
#   Returns False if nothing is playing.  Returns True if something was playing
#   and is now paused.
def pause_media(kodi_url, kodi_auth, headers):
    logging.debug("Entered kodi_library.pause_media().")

    is_playing = None
    request = None
    result = []

    # Find out if anything is playing.
    is_playing = _is_currently_playing(kodi_url, kodi_auth, headers)
    if not is_playing:
        logging.debug("Nothing is playing at this time.")
        return False
    is_playing = is_playing[0]
    logging.debug("Value of is_playing: %s" % str(is_playing))

    # Set up the payload.
    payload = {}
    payload["jsonrpc"] = "2.0"
    payload["id"] = 1
    payload["method"] = "Player.PlayPause"
    payload["params"] = {}
    payload["params"]["playerid"] = is_playing["playerid"]
    payload["params"]["play"] = False

    # If something is playing, toggle it.
    try:
        request = requests.post(kodi_url, auth=kodi_auth, headers=headers,
            data=json.dumps(payload))
        result = json.loads(request.text)
        result = result["result"]
        logging.debug("Response from Kodi: %s" % str(result))
    except:
        logging.warn("Failed to get response from Kodi!")
        return False
    if result["speed"] == 0:
        logging.debug("Successfully paused Kodi player subsystem %d." % payload["params"]["playerid"])
        return True

    # This seems kind of messy, but it's a fall-through for a no-op.
    return False

# unpause_media: If something is playing, pause it.  Takes three arguments, the
#   Kodi JSON RPC URL, an HTTP Basic Auth object, and a hash of headers.
#   Returns False if nothing is playing.  Returns True if something was paused
#   and is now playing.
def unpause_media(kodi_url, kodi_auth, headers):
    logging.debug("Entered kodi_library.unpause_media().")

    is_playing = None
    request = None
    result = []

    # Find out if anything is playing.
    is_playing = _is_currently_playing(kodi_url, kodi_auth, headers)
    if not is_playing:
        logging.debug("Nothing is playing at this time.")
        return False
    is_playing = is_playing[0]
    logging.debug("Value of is_playing: %s" % str(is_playing))

    # Set up the payload.
    payload = {}
    payload["jsonrpc"] = "2.0"
    payload["id"] = 1
    payload["method"] = "Player.PlayPause"
    payload["params"] = {}
    payload["params"]["playerid"] = is_playing["playerid"]
    payload["params"]["play"] = True

    # If something is playing, toggle it.
    try:
        request = requests.post(kodi_url, auth=kodi_auth, headers=headers,
            data=json.dumps(payload))
        result = json.loads(request.text)
        result = result["result"]
        logging.debug("Response from Kodi: %s" % str(result))
    except:
        logging.warn("Failed to get response from Kodi!")
        return False
    if result["speed"] >= 1:
        logging.debug("Successfully unpaused Kodi player subsystem %d." % payload["params"]["playerid"])
        return True

    # This seems kind of messy, but it's a fall-through for a no-op.
    return False

# stop_media: Stop whatever's playing right now.  Takes three arguments, the
#   Kodi JSON RPC URL, an HTTP Basic Auth object, and a hash of headers.
#   Returns False if nothing is playing.  Returns True if something was stopped.
def stop_media(kodi_url, kodi_auth, headers):
    logging.debug("Entered kodi_library.stop_media().")

    is_playing = None
    request = None
    result = {}

    # Find out if anything is playing.
    is_playing = _is_currently_playing(kodi_url, kodi_auth, headers)
    if not is_playing:
        logging.debug("Nothing is playing at this time.")
        return False
    is_playing = is_playing[0]
    logging.debug("Value of is_playing: %s" % str(is_playing))

    # Set up the payload.
    payload = {}
    payload["jsonrpc"] = "2.0"
    payload["id"] = 1
    payload["method"] = "Player.Stop"
    payload["params"] = {}
    payload["params"]["playerid"] = is_playing["playerid"]

    # If something is playing, stop` it.
    try:
        request = requests.post(kodi_url, auth=kodi_auth, headers=headers,
            data=json.dumps(payload))
        result = json.loads(request.text)
        result = result["result"]
        logging.debug("Response from Kodi: %s" % str(result))
    except:
        logging.warn("Failed to get response from Kodi!")
        result = None

    # Parse what comes back from Kodi.
    if result == "OK":
        return True
    else:
        return False

# ping_kodi: Function that uses the JSON RPC API to ping Kodi.  Takes three
#   arguments, the Kodi JSON RPC URL, an HTTP Basic Auth object, and a hash
#   of headers.  Returns True if it can, False if it can't.
def ping_kodi(kodi_url, kodi_auth, headers):
    logging.debug("Entered kodi_library.ping_kodi().")

    request = None
    result = {}

    # Set up the payload.
    payload = {}
    payload["jsonrpc"] = "2.0"
    payload["id"] = 1
    payload["method"] = "JSONRPC.Ping"

    # Ping the JSON RPC server.
    try:
        request = requests.post(kodi_url, auth=kodi_auth, headers=headers,
            data=json.dumps(payload))
        result = json.loads(request.text)
        result = result["result"]
        logging.debug("Response from Kodi: %s" % str(result))
    except:
        logging.warn("Failed to get response from Kodi!")
        result = None

    # Parse the response from the server.
    if result == "pong":
        logging.debug("Successfully pinged Kodi.")
        return True
    else:
        return False

# get_api_version: Function that uses the JSON RPC API to ask Kodi what
#   version of the JSON RPC API it's using.  Takes three arguments, the
#   Kodi JSON RPC URL, an HTTP Basic Auth object, and a hash of headers.
#   Returns "version x.y.z" if it can, None if it can't.
def get_api_version(kodi_url, kodi_auth, headers):
    logging.debug("Entered kodi_library.get_api_version().")

    request = None
    result = {}

    # Set up the payload.
    payload = {}
    payload["jsonrpc"] = "2.0"
    payload["id"] = 1
    payload["method"] = "JSONRPC.Version"

    # Ask the JSON RPC server what it thinks its version is.
    try:
        request = requests.post(kodi_url, auth=kodi_auth, headers=headers,
            data=json.dumps(payload))
        result = json.loads(request.text)
        result = result["result"]["version"]
        logging.debug("Response from Kodi: %s" % str(result))
    except:
        logging.warn("Failed to get response from Kodi!")
        result = None

    # Generate the response from the server.
    result = "version " + str(result["major"]) + "." + str(result["minor"]) + "." + str(result["patch"])
    return result

# _clear_current_playlist: Helper function that empties the current/default
#   media playlist.  This is something you have to do every time you want to
#   play something.  Takes three arguments, the Kodi JSON RPC URL, an HTTP
#   Basic Auth object, and a hash of headers.  Returns True if it worked, False
#   if it didn't for some reason.
def _clear_current_playlist(kodi_url, kodi_auth, headers):
    logging.debug("Entered kodi_library._clear_current_playlist().")

    request = None
    result = {}

    # Set up the payload.
    payload = {}
    payload["jsonrpc"] = "2.0"
    payload["id"] = 1
    payload["method"] = "JSONRPC.Version"
    payload["params"] = {}
    payload["params"]["playlistid"] = default_playlist

    try:
        request = requests.post(kodi_url, auth=kodi_auth, headers=headers,
            data=json.dumps(payload))
        result = json.loads(request.text)
        result = result["result"]
        logging.debug("Response from Kodi: %s" % str(result))
    except:
        logging.warn("Failed to get response from Kodi!")
        result = None

    # Parse what comes back from Kodi.
    if result == "OK":
        return True
    else:
        return False

# play_playlist: Function that tells Kodi to run whatever playlist (with a
#   complete path) it's given.  Takes four arguments, the Kodi JSON RPC URL, an
#   HTTP Basic Auth object, a hash of headers, and a filename to start playing.
#   Returns True if playback started, False if not.
def play_playlist(kodi_url, kodi_auth, headers, playlist):
    logging.debug("Entered kodi_library.play_playlist().")

    result = None
    payload = {}
    request = None

    # Wipe out the current playlist.
    result = _clear_current_playlist(kodi_url, kodi_auth, headers)
    if result:
        logging.debug("Cleared the scratch playlist.")
    else:
        logging.debug("Unable to clear the current scratch playlist.")

    # Set up the payload.
    payload["jsonrpc"] = "2.0"
    payload["id"] = 1
    payload["method"] = "Player.Open"
    payload["params"] = {}
    payload["params"]["item"] = {}
    payload["params"]["item"]["file"] = playlist

    try:
        request = requests.post(kodi_url, auth=kodi_auth, headers=headers,
            data=json.dumps(payload))
        result = json.loads(request.text)
        result = result["result"]
        logging.debug("Response from Kodi: %s" % str(result))
    except:
        logging.warn("Failed to get response from Kodi!")
        result = None

    # Parse what comes back from Kodi.
    if result == "OK":
        return True
    else:
        return False

def play_by_songid():

    # Set up the payload.
    payload = {}
    payload["jsonrpc"] = "2.0"
    payload["id"] = 1
    payload["method"] = "Player.Open"
    payload["params"] = {}
    payload["params"]["item"] = {}
    payload["params"]["item"]["songid"] = songid_from_library

if "__name__" == "__main__":
    pass
