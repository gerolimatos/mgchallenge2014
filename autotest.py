#!/usr/bin/env python
#
#
# Code Challenge for Mark Gerolimatos
# (SF Movie Database)
# mark@gerolimatos.com
# 650 703-4774
# (c) Mark Gerolimatos, save for code borrowed and credited
#
# October, 2014

from BaseImport import *
import json

#
#
# Autotest class. Tests out the three major components:
# -Autocomplete Ternary tree
# -SODA SoQL interface
# -Google Map interface
#
# Run once on module startup. Logs messages, does not cause any exceptions or errors,
# lest these errors be temporary.
# For instance, if a remote website is down when the test come up
#
# In other words, these tests assume a nominal service
#
# Note that while these tests are actually table driven, I have hardcoded the tables
# so that I do not need to manage the test case file. As an example of an auto test,
# this should suffice
#
class Autotests :
  @staticmethod
  def perform(**kwargs) :
    si = kwargs.get('soqlinterface')
    ac = kwargs.get('actable')
    gi = kwargs.get('googleinterface')
    MUSTPRINT("soql %s"%("is there" if si else ""))
    MUSTPRINT("googl %s"%("is there" if gi else ""))
    MUSTPRINT("autocomplete %s"%("is there" if ac else ""))
    # Search for some important strings in the autocomplete table:
    # vertigo, Vertigo, Vert, vert, and finally, V and v
    # Search for numbers.
    # Look for "Vertigo" in the title results.
    # This is the most important title of all, so we MUST make sure it's there.
    if (ac) :
      MUSTPRINT("TESTING Autocomplete:")
      # Autocomplete test format:
      # Query, the kind of query, and a regular expression to expect. 
      # If you expect no results, use 0 as the regexp
      Autotests.autocompleteTest(ac,
                     [{"query" : "v","title" :"Vertigo"},
                      {"query" : "V", "title" : "Vertigo"},
                      {"query" : "vert", "title" : "Vertigo"},
                      {"query" : "Vert",  "title" : "Vertigo"},
                      {"query" : "vertigo",  "title" : "Vertigo"},
                      {"query" : "Vertigo",  "title" : "Vertigo"},
                      {"query" : "Vertifrimbulmongers",  "title" : 0 },
                      {"query" : "Vertigofrimbulmongers",  "title" : 0 },
                      # And make sure the "the" remover is working
                      {"query" : "Jitney",  "title" : "A Jitney*" }
                    ])
    
      Autotests.autocompleteTest(ac,
                    [{ "query" : "2",  'locations' : "2417 Franklin Street"},
                      { "query" : "24",  'locations': "2417 Franklin Street"},
                      { "query" : "2417Franklin",  'locations' : 0}
                    ])

      # Spaces SHOULD NOT work, unless there really is a leading space
      Autotests.autocompleteTest(ac,
                    [{"query" : " 2", 'locations': None}])

      # And finally, make sure we're getting simultaneous titles and locations
      Autotests.autocompleteTest(ac,
                    [{"query" : "Pal", 'locations': "Palace of Fine*", 'title': "Pal Joey"}])

    # Now make sure we can get at least four map points for Vertigo
    if (gi and si) :
      MUSTPRINT("TESTING Map Search:")
      # Geo test format:  
      # title/location, minimum number to receive (0 will result in a test failure if results are returned)
      # and a "has" regexp to check the results against
      Autotests.geotests(si, gi,
                    [{"title" : "vertigo", "count" : 5, "has": "Fort Point*" },
                     {"locations" : "coit tower", "count" : 5, "has" : "Pal Joey"},
                     {"locations" : "coit towerasdfasdfasdfasdf", "count" : 0}
                    ])

######################## IMPORTANT NOTE ################################
######################## IMPORTANT NOTE ################################
######################## IMPORTANT NOTE ################################
# This one actually fails for real! The SFMovies SoQL query engine pukes on this title. Tried everything,
# backslahes, wildcards, etc. Absolutely no luck.
#{"title" : "What's Up Doc?", "count" : 0}
# Check it out...the SoDA query machine is busted
#> curl 'http://data.sfgov.org/resource/yitu-d5am.json?$select=locations%2C+title%2C+release_year&$where=title=What'"'"'s+Up+Doc?'"'"'&$order=locations&$limit=50000'
#{
#  "code" : "query.compiler.malformed",
#  "error" : true,
#  "message" : "Error, could not parse SoQL query \"select locations, title, release_year from #yitu-d5am where title=What's Up Doc?' order by locations limit 50000\"",
#  "data" : {
#    "query" : "select locations, title, release_year from #yitu-d5am where title=What's Up Doc?' order by locations limit 50000"
#  }
#}
################# AND NOW, BACK TO YOUR REGULAR BROADCAST #############


  @staticmethod
  def autocompleteTest(ai, testList) :
    try:
      for test in testList :
        query = test.get('query')
        result = ai.doAutocomplete(query)
        for testtype in ['title', 'locations'] :
          regexp = test.get(testtype)
          # No test for this kind
          if (regexp is None) :
            continue
          data = result[testtype]
          if (regexp is 0) :
            if (data) :
              MUSTPRINT("Autocomplete test fail for \"%s\": %s list not empty"%(regexp,testtype), True)
            else :
              INFOPRINT("Autocomplete test SUCCESS for %s \"%s\""%(testtype, regexp), 9)
          else :
            findcount = 0
            for datum in data :
              if (re.match(regexp,datum)) :
                findcount += 1
            if (findcount == 0) :
              MUSTPRINT("Autocomplete test fail for \"%s\": not found in %s"%(regexp,testtype), True)
            else :
              INFOPRINT("Autocomplete test SUCCESS for %s \"%s\""%(testtype, regexp), 9)
    except Exception as e:
      MUSTPRINT("Autocomplete Test Fail for \"%s\": Exeption: %s"%(json.dumps(testList),str(e)), True)
      # Just for now
      raise e

  @staticmethod
  def geotests(si, gi, testList) :
    for test in testList :   
      errmsg = ""
      for testtype in ['title', 'locations'] :
        query = test.get(testtype)
        if not query :
          continue
        if query and testtype == "title" :
          results = si.doTitleSearch(query)
        elif query :
          results = si.doLocationSearch(query)
        countNeeded = test.get('count') if test.get('count') else 0
        matchNeeded = None if countNeeded == 0 else test.get('has')
        if test.get('count') is not None :
          if len(results) < countNeeded :
            errmsg += ": Expected at least %d results, got %d"%(countNeeded, len(results))
          if len(results) and test.get('count') == 0:
            # If we didn't get an error code, then something's amiss
            if not results[0].get('error_code'):
              errmsg += ": Expected no results, got %d"%(len(results))
              INFOPRINT("EXPECTED NOTHING, GOT: \"%s\""%json.dumps(results), 9)
        for result in results :
          try :
            geoinfo = gi.geoLookup(result['locations'], False)
            if (not geoinfo) :
              errmsg = ", " + "empty result"
              INFOPRINT("Empty result looking for %s"%result['locations'], 9)
            elif geoinfo.get('errmsg'):
              errmsg += ": " + geoinfo.get('errmsg')
              INFOPRINT("Got %s for %s"%(geoinfo.get('errmsg'),result['locations'], 9))
            elif matchNeeded and re.match(matchNeeded, str(result.get('name'))) :
              # Found it!
              INFOPRINT("FOUND %s",matchNeeded)
              matchNeeded = None
          except Exception as e:
            errmsg += ": " + str(e)
        if (matchNeeded) :
            errmsg += ": " + "Did not find " + matchNeeded
        if (errmsg) :
            errmsg = "GEO %s test failed for %s %s"%(testtype, str(test.get(testtype)), errmsg)
        if (errmsg) :
          MUSTPRINT(errmsg, True)
        else :
          INFOPRINT("Geo %s test for \"%s\" SUCCESS"%(testtype,query),9)

