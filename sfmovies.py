#!/usr/bin/env python
#
# Code Challenge for Mark Gerolimatos
# (SF Movie Database)
# mark@gerolimatos.com
# 650 703-4774
# (c) Mark Gerolimatos, save for code borrowed and credited
#
# October, 2014
#
#
# Main file for Mark Gerolimatos' SF Movie Database code challenge.
#

###
### IMPORTS
###

# This one contains some basic types we would use in the global space
from BaseImport import *

# This is the Google App Engine API
import webapp2

# Url and JSON encoders/decoders (we don't use urllib for communication)
import urllib, json

# Simplified URL API
# http://docs.python-requests.org/en/latest/
import requests

# GoogleMaps API. Not imported here, but links are given so that
# they're all in one place
# https://pypi.python.org/pypi/pygeocoder
# http://code.xster.net/pygeocoder/wiki/Home
# Note that for the GoogleMaps API, it is completely sufficient
# to use the embed code listed here:
# https://developers.google.com/maps/documentation/embed/guide
# My Google API key is AIzaSyBmyoN1EKcoR6922TlDKBGVFHReOwBvZOs
# My API console
# https://code.google.com/apis/console/?noredirect#project:811214123559

# Our modules
# SimpleCache is just a dict() wrapper that lets you pass it by ref
# LRUCache is just what it sounds like
# ExpiringCache is a cache whose entries can expire
# 
from simplecache import *

# The SoQLInterface is my own interface to the SoQL SODA query language
# The SoQL interface on the Git site isn't much better, if not worse
from soqlinterface import *

# This is a small library to do autocompletion
from autocomplete import *

# This is the interface to the GoogleMaps API
from googleinterface import *

# I *WOULD LOVE* to use the IMDB api, but it's apparently not a public thing,
# so I am not going to waste my time on it


#############################################################
##
## Global Data
##
#############################################################
# These are the URLs we use to access the City Movie Data
# Base URL gets us the metadata only.
sitename = "data.sfgov.org"
datasetname = "yitu-d5am"
baseurl="https://" + sitename + "/api/views/" + datasetname

# We will use this one to get metadata to determine if we have to
# re-scrape the autocomplete list
metadataurl = baseurl

# This is the URL that gets us all the necessary data rows (as well as the 
# metadata).
rowsurl=baseurl+"/rows.json"

# This needs to be done once on startup, and then done repeated on a separate
# thread. Initial load done now, but separate thread not yet done (if I ever do that,
# that is a feature to drop)
# Note that time limitations and inability to properly test changes
# in the data and metadata (hasn't happened since I started writing this)
# make backend re-scraping ill-advised at this time

actable = AutocompleteTable(sitename, datasetname)
actable.fetchAutocomplete()
printInterval("Fill Autocomplete Table")

# Now run the autotests on startup
from autotest import Autotests
Autotests.perform(
          actable = actable, 
          soqlinterface = SoQLInterface(sitename, datasetname),
          googleinterface = GoogleMapInterface())

# This is the page that The Google's App Engine will interact with us
#### Main page class ####
class MainPage(webapp2.RequestHandler):

  # MY LRUCaches are threadsafe, so we can make them static
  urlCache = LRUCache(maxsize=100)

  # There may be a *LOT* of autocomplete queries, so store them in their own cache.
  # Because they need to be fast, use a simple cache (which prevents synchronization
  # by providing no real value over a normal dict). We will rely on an outside agent
  # to invalidate the cache when the metadata has changed
  #
  # Repeat: impossible to test, since metadata has not changed, so for this 
  # challenge (only), this will not be performed. Note that simply restarting the server
  # once a day gets us this effect.
  #
  autccompleteCache = SimpleCache()

  def __init__(self, request=None, response=None) :
    global datasetname
    global sitename
    super(MainPage, self).__init__(request, response)
    self.si = SoQLInterface(sitename, datasetname)
    self.caughtCount = 0
    # If we have 10 failures without a success, we're just dead, so go ahead, throw
    # an exception, and let The Google restart us as necessary
    self.maxfailures = 10

  # This is the callback called by the webapp2 API when we receive a get call.
  # we only support get.
  def get(self):
    INFOPRINT("GOT URL: %s"%self.request.url,3)
    try:
      # Build up a query, and check against the LRURL (clever, huh?) cache to see
      # if we already have the results.
      path = self.request.path
      queries = self.request.query_string
      command = self.request.get('cmd').lower()
      # Be sure to use the correct cache!
      if (command == "query") :
        cache = MainPage.autocompleteCache
      else :
        cache = MainPage.urlCache
      key = UrlEncoder.decode("%s?%s"%(path,queries))

      # Now look the item up in the correct cache
      result = cache.get(key)
      if not result :
        INFOPRINT("CACHE MISS ON \"%s\""%key,2)
        # Call the internal worker function to actually do the work
        result = self.getInternal()
        # If we got here, then we didn't fail...
        # True, this caughtCount is not thread safe, but no big deal: if thread safety
        # is an issue for CAUGHT COUNT (i.e. lots of exceptions), then we WANT it to bomb out!
        self.caughtCount = 0
        # No output? don't cache it!
        if (result is None) :
          return

        # Now cache the result, but ONLY if there was no error message!
        errmsg = result.get('errmsg')
        if (not errmsg) :
          INFOPRINT("Storing \"%s\" in cache"%key, 2)
          cache.put(key, result)
        else :
          # If you have info turned on, you will see this. Don't want to start yammering on the
          # log if the remote site is down.
          INFOPRINT("Error performing %s search: %s"%(command,result.get('errmsg')),5)
      else :
        ### CACHE HIT! ###
        INFOPRINT("CACHE HIT ON \"%s\""%key,2)
        # Copy in the conten-type header from the cached version
        # getInternal's sub functions did this for us on the previous run
        self.response.headers['Content-Type'] = result['headers'].get('Content-Type')
        
      # Now print out the response lines! This is your data to the client
      for line in result['body'] :
        self.response.write(line + "\n")
        
    except:
      self.caughtCount += 1
      self.response.clear()
      self.response.set_status(500, "Sorry, internal failure")
      if (self.caughtCount >= self.maxfailures) :
        raise


  # Get internal: the function that determines which map call to make.
  # On most failures, it will bring up the welcome screen (a map of SF), so that
  # the user isn't presented with nasty 404's :-)
  def getInternal(self):
      
    command = self.request.get('cmd')
    if (command) :
      command = UrlEncoder.decode(command).lower()

    # "query" is passed to us by the jquery autocomplete package.
    # this is equivalent to our "ac" command
    query = self.request.get('query')
    query = UrlEncoder.decode(query)
    if (query) :
      command = "ac"

    # We could do a switch statement or some fancy function table,
    # but why?

    # Autocompletion. This needs to be as fast as possible,
    # so it comes immed
    # Do this one first, as it needs the fastest response
    if (command is "ac") :
      inp = query
      self.response.headers['Content-Type'] = 'application/json'
      if (ISLEVEL(1)) :  INFOPRINT("AUTOCOMPLETE, GOT QUERY \"%s\""%inp,1)
      holder = DictHolder()
      # Pass by ref to speed up the lookup as much as possible
      responseDict = holder.dictObj
      self.doAutocomplete(inp, holder)
      string = json.dumps(holder.dictObj)
      result = dict()
      result['body'] = [string]
      result['headers'] = self.response.headers
      # This WILL get cached
      return result

    # All other commands take an optional "input" parameter
    inp = self.request.get('input')
    if (inp) :
      inp = UrlEncoder.decode(inp)

    # Help command. See how nice I am?
    if (command == "help") :
      self.response.headers['Content-Type'] = 'text/plain'
      outputlist = list()
      outputlist.extend([
        'COMMANDS',
        '/?cmd=start: initialize the server',
        '/?cmd=help: this message',
        '/?cmd=debug&input=<number>: set debug level to integer number. 0 means off',
        '/?cmd=ts&input=<name>: do a search of filming locations for given title',
        '/?cmd=ls&input=<name>: do a search of films made at a given title',
        '/?query=<input>: do an autocomplete search from the autocomplete database',
        '/: show the welcome (initial) screen'
       ])
      # Do our own printout so that people will not cache this one (in case something changes based
      # on debug levels. Hasn't happened yet, but it might)
      for line in outputlist :
        self.response.write(line + "\n")
      # Nothing else to write out
      return None

    # Startup command
    # Typically, this would be started by whatever daemon or build package (Jenkins, etc)
    # after installation
    # This helps insure that both Python and the Autocomplete table is initialized properly, 
    # so that you won't get a big ol' delay on the first query
    if (command == "start") :
      responseDict = dict()
      self.response.headers['Content-Type'] = 'application/json'
      responseDict['result'] = "started"
      # Do our own printout so that people will not cache this one
      self.response.write(json.dumps(responseDict))
      return None


    # Set debug level
    if (command == "debug") :
      inputint = int(inp)
      SETLEVEL(inputint)
      self.response.headers['Content-Type'] = 'text/plain'
      self.response.write("Debug Level set to %d"%inputint)
      # DEFINITELY DO NOT cache this one!
      return None
    

    # Just show SF proper if the command is empty or no string was provided
    # Essentially a 404 preventer
    if (not command or not inp) :
      holder = DictHolder()
      responseDict = holder.dictObj
      result = dict()
      bodyfail = self.doWelcomeScreen('')
      result['body'] = bodyfail.get('body')
      result['errmsg'] = bodyfail.get('errmsg')
      result['headers'] = self.response.headers
      return result

    # Title Search
    elif (command == "ts"):
      result = dict()
      errorString = self.illegalInput(inp,"title")
      if not errorString :
        bodyfail = self.doTitleSearch(inp)
      # If an error was reported, bring up the welcome screen
      if (errorString or bodyfail.get('errmsg')) :
        if (not errorString) :
          errorString = bodyfail.get('errmsg')
        bodyfail = self.doWelcomeScreen(errorString)
      result['body'] = bodyfail.get('body')
      result['errmsg'] = bodyfail.get('errmsg')
      result['headers'] = self.response.headers
      return result

    elif (command == "ls"):
      result = dict()
      errorString = self.illegalInput(inp,"location")
      # If an error was reported, bring up the welcome screen
      if not errorString :
        bodyfail = self.doLocationSearch(inp)
      if errorString or bodyfail.get('errmsg') :
        if not errorString:
          errorString = bodyfail.get('errmsg')
        bodyfail = self.doWelcomeScreen(errorString)
      result['body'] = bodyfail.get('body')
      result['errmsg'] = bodyfail.get('errmsg')
      result['headers'] = self.response.headers
      return result


  # Checks for illegal input. Found when I got creative and tried out "What's Up, Doc?" only to find
  # out that the SFMovie SoDA engine didn't handle it. Sigh.
  def illegalInput(self, inp, searchType) :
    if not inp :
      return ""
    decodedString = UrlEncoder.decode(inp)
    strippedString = decodedString.strip()
    if (decodedString != strippedString) :
      return "%s query \"%s\" must not have padded input"%(searchType,decodedString)
    # This is the ideal regexp, but really, all we acare about is there being a tick or quote in the middle
    # of the string
    #if (re.match("['\"].*'.*['\"]", decodedString)) :
    try :
      if (decodedString.index('\'') > 0) :
        return "Can't find %s \"%s\", SFMovie Database does not support queries with ticks in them"%(searchType,decodedString)
    except:
      # An exception means it's not there. Can't use "in" because an initial tick is totally leagal
      return ""

    # Quotes appear to be okay. Whatever.
    #try :
      #if (decodedString.index('"') > 0) :
      #  return "Can't find %s \"%s\", SFMovie Database does not support queries with quotes in them"%(searchType,decodedString)
    #except:
      # An exception means it's not there. Can't use "in" because an initial tick is totally leagal
      #return ""


  # Actually do the location search.
  # Takes a
  def doLocationSearch(self, inp) :
    self.response.headers['Content-Type'] = 'text/html'

    # This is the one doing all the work
    resultList = self.si.doLocationSearch(inp)

    if (not resultList) :
      return self.doWelcomeScreen("Sorry, couldn't find location %s"%inp)
    if (resultList[0].get('error_code')) :
      tryAgainString = resultList[0].get('try_again')
      return self.doWelcomeScreen("Sorry, couldn't find location %s: %s.%s"%(inp, 
                                                             resultList[0].get('error_code'),
                                                             ("Please try again later" if tryAgainString else "")))
    outlist = ["<!DOCTYPE html>", "<html>"]
    outlist.extend(self.generateHeader())
    gmi = GoogleMapInterface()
    infotitle = ""
    title = "Location: %s"%inp
    for result in resultList :
      year=result.get('release_year')
      t = result.get('title')
      title=("%s%s"%(t," ("+year+")" if year else ""))
      href="<a href=\"/?cmd=ts&input=%s\">%s</a><br>"%(UrlEncoder.encode(t),title)
      infotitle += (href)
    # Even if the marker is outside of the city limits, show it anyway...
    marker = gmi.geoLookup(inp, True)
    errmsg = marker.get('errmsg')
    marker['name'] = inp
    # And create the map
    outlist.extend(GoogleMapInterface.mapHeader(title, [marker], 
                                                searchCmd=None,
                                                infowindowtitle=infotitle,
                                                infoup="marker0"))
    outlist.append("</head>");
    # Now do the body. This is pretty simple code
    outlist.extend(self.generateBody(label="Movies filmed at " + inp))
    return {'body' : outlist, 'errmsg' : errmsg}

  # Welcome screen brings up a map of SF with no markers,
  # and puts up the message fron inp.
  # it also returns it as an error so that 
  # the results won't get cached
  def doWelcomeScreen(self, inp) :
    self.response.headers['Content-Type'] = 'text/html'
    resultList = self.si.doLocationSearch('')
    outlist = ["<!DOCTYPE html>", "<html>"]
    outlist.extend(self.generateHeader())
    gmi = GoogleMapInterface()
    if not inp:
      inp = "Movie Locations Within San Francisco"
      errmsg = None
    else :
      errmsg = inp
    outlist.extend(GoogleMapInterface.mapHeader(inp, [], 
                                                searchCmd=None,
                                                ))
    outlist.append("</head>");
    # Now do the body. This is pretyt simple code
    outlist.extend(self.generateBody(label=inp))
    return { 'body' : outlist, 'errmsg' : errmsg }


  # Do title search: does a search from the SoQL interface,
  # And for each marker does a GeoLookup
  # Finally, it passes all those markers into the map function in the GoogleMapInterafce
  # and adds in a simple boxy
  def doTitleSearch(self, inp) :
    self.response.headers['Content-Type'] = 'text/html'
    resultList = self.si.doTitleSearch(inp)
    if (not resultList) :
      return self.doWelcomeScreen("Sorry, couldn't find title %s"%inp)
    if (resultList[0].get('error_code')) :
      tryAgainString = resultList[0].get('try_again')
      return self.doWelcomeScreen("Sorry, couldn't find title %s: %s.%s"%(inp, 
                                                             resultList[0].get('error_code'),
                                                             ("Please try again later" if tryAgainString else "")))
    outlist = ["<!DOCTYPE html>",
               "<html>"]
    outlist.extend(self.generateHeader())
    gmi = GoogleMapInterface()
    markerlist = list()
    title = "Map of Locations for \"%s\""%inp
    # Sometimes, brackets are a good thing
    slelems = list()
    markernum = 0
    errmsg = None
    for result in resultList :
    #{
      # Strange...a result without a location. Bad data!
      if not result.get('locations') :
        continue
      geoinfo = gmi.geoLookup(result['locations'], False)
      # Prevent needless calculation of strings
      if (ISLEVEL(1))  : INFOPRINT("geoinfo for '%s' = %s"%(result['locations'],str(geoinfo)),1)
      if (not geoinfo):
        # Not there!
        continue;
      else :
      #{
        errmsg = geoinfo.get('errmsg')
        if (geoinfo.get('name')) :
          geoinfo['name'] = result['locations']
          markerlist.append(geoinfo)
          markernum += 1
        # If name is blank, then we are outside SF, so drop it
      #}
    #}
    # Now create the map..
    outlist.extend(GoogleMapInterface.mapHeader(title, markerlist, 
                                                searchCmd="ls"))
    outlist.append("</head>");
    # Now do the body. This is pretyt simple code, so we just duplicate it
    outlist.extend(self.generateBody(label=inp + ": filming locations within San Francisco"))
    # If we got at least one result, then there was no failure
    return {'body' : outlist, 'errmsg' : errmsg}


  # Generates all the nice nice Javascript and CSS headers that go in each page.
  # returns the data as a list of strings for either caching or sending to the client
  def generateHeader(self) :
    outlist = list()
    # Taken from:
    # http://stackoverflow.com/questions/8100576/how-to-check-if-dom-is-ready-without-a-framework
    # https://www.devbridge.com/sourcery/components/jquery-autocomplete/
    # http://jquery.com/download/
    # http://www.jqueryrain.com/2012/03/35-best-ajax-jquery-autocomplete-tutorial-plugin-with-examples/
    outlist.extend([
          '<head>',
          '<link rel="stylesheet" type="text/css" href="http://www.gerolimatos.com/cgi/autocomplete.css">',
          # The Google has ajax available. Use that, they can serve it faster.
          #'<script type="text/javascript" src="http://www.gerolimatos.com/cgi/jquery.js"></script>',
          '<script src="//ajax.googleapis.com/ajax/libs/jquery/1.10.2/jquery.min.js"></script>',
          '<script src="//ajax.googleapis.com/ajax/libs/jqueryui/1.11.1/jquery-ui.min.js"></script>',
          '<script type="text/javascript" src="http://www.gerolimatos.com/cgi/jquery.autocomplete.js"></script>',
          '<script>',
          'function doAutocompleteInit() {',
          '     var options, a;',
          '     jQuery(function(){',
          "         options = { serviceUrl:'/' , ",
          "                     onSelect: function(suggestion){ ",
          "            var url = '/?cmd=' + encodeURIComponent(suggestion.data) + '&input=' + encodeURIComponent(suggestion.value) +'';",
          "                         window.location = url; }",
          "          }",
          "         a = $('#query').autocomplete(options);",
          '    });',
          '}',
          #'if (document.readyState === "complete") { doAutocompleteInit(); }',
          #'else {',
          '  document.addEventListener("DOMContentLoaded", doAutocompleteInit, false);',
          # This doesn't seem to work for some reason...
          #'  window.addEventListener("onload", function() {doAutocompleteInit();}, false);',
          #'}',
          '</script>',
          ])
    return outlist


  # The body is purposely simple, and will be added on to if more time is avaialable. Working with 
  # browsers takes more time than is practical in the time alotted
  #
  def generateBody(self, **kw) :
    # Autocomplete jquery code courtesy of:
    # https://www.devbridge.com/sourcery/components/jquery-autocomplete/
    # https://github.com/devbridge/jQuery-Autocomplete
    outlist = list()
    name = kw.get('label')
    outlist.extend([
          "<body>",
          '<div id="textpane">',
          '<legend id="namelabel">' + str(name) + '</legend>',
          '<div class="container">',
            '<div class="autocomplete-wrapper" id="">',
            '<label for="query">Start a-Typin!</label> ',
            '<input class="text-field" id="query" name="query" size="50" maxlength="80" placeholder="Start typing away!" type="text" /></div>',
          #'Type Here ->&nbsp;<input type="text" name="TypeHere" size="50" maxlength="50" id="query">',
          '</div>',
          '</div>',
          '<div id="map-canvas"></div>',
          "</body>",
          "</html>"])
    return outlist


  # Return a JSON object in the format expected by JQuery-autocomplete
  # returns by reference thru holder to prevent any nasty copy operations
  # imposed by Python (shoudl be small, but just to be safe)
  def doAutocomplete(self, inp, holder) :
    global actable
    if (not inp) :
      matches = { 'title' : [], 'locations' : [] }
    else :
      matches = actable.doAutocomplete(inp)
    outputlist = list()
    titles = matches['title']
    locations = matches['locations']
    # Prevent needless generation of strings
    if (ISLEVEL(1)) : INFOPRINT("THERE ARE %d titles and %d locations"%(len(titles),len(locations)),1)
    while len(titles) > 0 or len(locations) > 0 :
    #{
      title = None if not titles else titles[0]
      location = None if not locations else locations[0]
      record = dict()
      if (title is None) :
        record['value'] = locations.pop(0)
        record['data'] = "ls"
      elif (location is None) :
        record['value'] = titles.pop(0)
        record['data'] = "ts"
      elif (location > title) :
        record['value'] = titles.pop(0)
        record['data'] = "ts"
      else :
        record['value'] = locations.pop(0)
        record['data'] = "ls"
      outputlist.append(record)
    #}
    holder.dictObj['query'] = "Unit"
    holder.dictObj['suggestions'] = outputlist
        




### And this is our link to the outside world!
application = webapp2.WSGIApplication([
    ('/', MainPage),
], debug=False)
