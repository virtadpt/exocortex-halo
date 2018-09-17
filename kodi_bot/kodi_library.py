#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# media_library.py - Kodi Bot module which does the heavy lifting of acquiring,
#   organizing, and manipulating a media library from Kodi.  Kodi doesn't offer
#   any of this functionality so we have to do it ourselves.
#
#   This is part of the Exocortex Halo project
#   (https://github.com/virtadpt/exocortex-halo/).

# By: The Doctor <drwho at virtadpt dot net>
#       0x807B17C1 / 7960 1CDC 85C9 0B63 8D9F  DD89 3BD8 FF2B 807B 17C1

# License: GPLv3

# v1.0 - Initial release.

# TO-DO:
# -

# Load modules.
import logging
import os

from fuzzywuzzy import fuzz

# Functions.

# get_media_sources(): Generate a list of media sources on the Kodi box.  From
#   the Kodi docs, there are only two we have to care about, video and music.
#   I'm using the canonical Kodi names for consistency's sake.  Takes one
#   argument, a Kodi client object.  Returns a hash table containing the media
#   sources the Kodi box has configured.
def get_media_sources(kodi):
    logging.debug("Entered media_library.get_media_sources().")

    sources = {}
    sources["video"] = []
    sources["music"] = []
    tmp = None

    # Build a list of video sources on the Kodi box.
    tmp = kodi.Files.GetSources("video")
    if "sources" not in tmp["result"]:
        logging.warn("'video' is not a registered media source.")
    else:
        for i in tmp["result"]["sources"]:
            sources["video"].append(i["file"])

    # Build a list of music sources on the Kodi box.
    tmp = kodi.Files.GetSources("music")
    if "sources" not in tmp["result"]:
        logging.warn("'music' is not a registered media source.")
    else:
        for i in tmp["result"]["sources"]:
            sources["music"].append(i["file"])

    logging.debug("Known media sources: %s" % str(sources))
    return sources

# build_media_library(): Function that builds the local media library, because
#   there's no straightforward way to query Kodi.  Takes four args, a reference
#   to a Kodi client object, a hash table of media sources, a hash table
#   representing the media library, and a list of directories to ignore.
#   Returns a new copy of the media library.
def build_media_library(kodi, sources, media_library, exclude_dirs):
    logging.debug("entered kodi_library.build_media_library().")
    logging.info("Now indexing media library... this could take a while.")

    # Set up categories in the media library.
    media_library["artists"] = []
    media_library["albums"] = []
    media_library["audio"] = []
    media_library["movies"] = []
    media_library["music"] = []
    media_library["musicvideos"] = []
    media_library["songs"] = []
    media_library["tv"] = []
    media_library["video"] = []

    # For every media source...
    for source in sources.keys():
        # For every directory in every media source...
        #logging.debug("Now scanning media source %s..." % source)
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
            tmp = kodi.Files.GetDirectory(directory)

            # Catch file system errors, like file permissions.
            if "error" in tmp.keys():
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
                if k["file"].endswith("/"):
                    #logging.debug("Found subdirectory %s in the media library.  Adding it to the queue to index later." % k["file"])
                    sources[source].append(k["file"])
                    continue

                # Otherwise, add the media to the library.
                media_tmp = {}
                media_tmp["file"] = k["file"]
                media_tmp["label"] = k["label"]
                media_library[source].append(media_tmp)

    return media_library

# get_artists(): Gets the directory of artists from the Kodi media database.
#   Takes one argument, a Kodi client object.  Returns an array of artists.
def get_artists(kodi):
    logging.debug("Entered kodi_library.get_artists().")
    artists = None
    list_of_artists = []

    try:
        artists = kodi.AudioLibrary.GetArtists()
    except:
        logging.debug("No artists in audio library - that's weird.")
        return None

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
#   Takes one argument, a Kodi client object.  Returns an array of albums.
def get_albums(kodi):
    logging.debug("Entered kodi_library.get_albums().")
    albums = None
    list_of_albums = []

    try:
        albums = kodi.AudioLibrary.GetAlbums()
    except:
        logging.debug("No albums in audio library - that's weird.")
        return None

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
#   Takes one argument, a Kodi client object.  Returns an array of songs.
def get_songs(kodi):
    logging.debug("Entered kodi_library.get_songs().")
    songs = None
    list_of_songs = []

    try:
        songs = kodi.AudioLibrary.GetSongs()
    except:
        logging.debug("No songs in audio library - that's weird.")
        return None

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
#   Takes one argument, a Kodi client object.  Returns an array of movies.
def get_movies(kodi):
    logging.debug("Entered kodi_library.get_movies().")
    movies = None
    list_of_movies = []

    try:
        movies = kodi.VideoLibrary.GetMovies()
    except:
        logging.debug("No movies in video library - that's weird.")
        return None

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
#   Takes one argument, a Kodi client object.  Returns an array of TV shows.
def get_tv_shows(kodi):
    logging.debug("Entered kodi_library.get_tv_shows().")
    tv = None
    list_of_tv_shows = []

    try:
        tv = kodi.VideoLibrary.GetTVShows()
    except:
        logging.debug("No genres in video library - that's weird.")
        return None

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
#   Kodi media database.  Takes one argument, a Kodi client object.  Returns an
#   array of genres and genre ID codes.  Why this isn't part of the media
#   library itself, I don't know.
def get_audio_genres(kodi):
    logging.debug("Entered kodi_library.get_audio_genres().")
    genres = None
    list_of_genres = []

    try:
        genres = kodi.AudioLibrary.GetGenres()
    except:
        logging.debug("No genres in audio library - that's weird.")
        return None

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
#   Kodi media database.  Takes one argument, a Kodi client object.  Returns an
#   array of genres and genre ID codes.
def get_video_genres(kodi):
    logging.debug("Entered kodi_library.get_video_genres().")
    genres = None
    list_of_genres = []

    try:
        genres = kodi.VideoLibrary.GetGenres()
    except:
        logging.debug("No genres in video library - that's weird.")
        return None

    if "genres" not in genres["result"]:
        logging.warn("No video genres found in library.")
        return None

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
                break

    logging.debug("Value of result: %s" % str(result))
    return result

# search_media_library_artists(): Takes a search term, a reference into a
#   section of the media library, and a minimum match confidence and scans for
#   matches.  Returns a hash table containing the media's internal entry.  This
#   is a separate function because the "artists" part of the media library
#   doesn't use "label" as a key, so there's no good generic way of doing it
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
        if match > confidence:
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

if "__name__" == "__main__":
    pass
