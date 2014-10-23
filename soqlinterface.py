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

import  requests, urllib, json
from  BaseImport import *
from simplecache import *

#
# This class provides us with an interface to a SODA site's query intervfce
# It is pretty simple, supporting a get operation only
#
#
class SoQLInterface :
  # Class static member that will hold the cache of all our requests.
  # By default, members of an expiring cache go away after 10 days
  # ExpiringCache is threadsafe
  cache   = ExpiringCache(864000)

  # Takes a URL and return a list of dicts that correspond to
  # each result
  # If there was an exception, return NULL. No error messages are printed
  # out
  # If there are no results, the empty list results
  def __init__(self, hostname, datasetname) :
    self.baseurl = "http://" + hostname + "/resource/" + datasetname + ".json"
    # we create our own decoder lest there be unadvertised race conditions
    # when two threads request a decode.
    self.decoder = json.JSONDecoder()
  

  #
  # Internal function that builds up a query based on the 6 specified clauses.
  # These clauses roughly match SQL, hence "SoQL"
  #
  def doGet(self,
            cacheExpiration=None,
            selectClause=None,
            whereClause=None,
            orderClause=None,
            groupClause=None) :
    url = self.baseurl
    queryChar = "?"
    if (selectClause) :
      url += queryChar + "$select=" + UrlEncoder.encode(selectClause)
      queryChar = "&"
    # Where needs to come before group
    if (whereClause) :
      url += queryChar + "$where=" + UrlEncoder.encode(whereClause)
      queryChar = "&"
    # Group needs to come before order
    if (groupClause) :
      url += queryChar + "$group=" + UrlEncoder.encode(groupClause)
      queryChar = "&"
    if (orderClause) :
      url += queryChar + "$order=" + UrlEncoder.encode(orderClause)
      queryChar = "&"
    # Frankly, 50000 is good enough: we don't have to worry about paging.
    url += queryChar + "$limit=50000"

    # Look up in the cache first
    cacheEntry = SoQLInterface.cache.get(url)

    if (cacheEntry) :
      # Prevent unnecessary generation of a string
      if (ISLEVEL(3)) : INFOPRINT("Using cache for URL %s"%url,3)
      return cacheEntry

    try:
      # The mysterious 6.05 seconds on connect timeout is to prevent
      # TCP from opening the connetion just as we give up
      response = requests.get(url, timeout=(6.05, 22))
    except requests.exceptions.Timeout:
      return [{'error_code' : 'timeout', 'try_again': True}]
    except Exception as e:
      return [{'error_code' : str(e), 'try_again': True}]

    # example error from SoDA
    #{
    #  "code" : "query.execution.queryTooComplex",
    #  "error" : true,
    #  "message" : "No multi-column conditions are allowed",
    #  "data" : {
    #    "reason" : "validation.multi-column-condition"
    #  }
    #}

    allobjs = self.decoder.decode(response.content)
    if (response.status_code < 200 or response.status_code >= 300) :
      if type(allobjs) is dict and allobjs.get("error") :
        return [{"error_code" : "query error"}]
    # Make sure we have a list if a singleton is returned
    # Could also do type reflection: if (type(allobjs) is dict...)
    retval = list()
    retval.extend(allobjs)
    
    # Do not cache if one was an error
    dontCache = 0
    for obj in allobjs:
      if (obj.get('error')) : dontCache = 1
    if dontCache == 0 :
      SoQLInterface.cache.put(url, retval, ttlSeconds=cacheExpiration)
    return retval

  # internal function that does a dual-purpose location or title search
  def doSearch(self, key, value, antiKey, cacheExpiration=None) :
    resultList = self.doGet(
                selectClause='locations, title, release_year',
                whereClause=key+"='"+value+"'",
                orderClause=antiKey,
                cacheExpiration=cacheExpiration)
    return resultList


  # Public function that does a location search, returning all the
  # titles that filmed in this location
  # This can change quite frequently (people make movies in Fisherman's Wharf
  # all the time), and so the value should not be cached for a long period
  # of time
  def doLocationSearch (self, value) :
    # Hold the values for a day
    resultList = self.doSearch("locations", value, "title", cacheExpiration=86400)
    return resultList


  # Public function that does a title search, returning all the 
  # locations that this movie was filmed at. Movies don't suddenly change
  # locations, and thus the only change might be flaws in the data that were 
  # repaired. That can be caught separately by a metadata version detector
  # (necessary for the autocompete database)
  def doTitleSearch(self, value) :
    resultList = self.doSearch("title", value, "locations")
    return resultList


# This function COULD be made part of the SoQL class, but is made global 
# to keep code short, and prevent a bunch of "SoQLInterface." all over 
# the place

# Relation: creates a string of the proper format. Essentially turns
# a prefix-notation relation into the proper infix, prefix or postfix
# based on the verb
def relation(verb, leftvalue, rightvalue="") :
  retstring = ""
  if (verb is "IS NULL" or verb is "IS NOT NULL") :
    retstring =  str(leftvalue) + verb
  elif (verb in ["sum", "count", "avg", "min", "max"] ) :
    retstring = verb + "(" + leftvalue + ")"
  elif (verb is "AS") :
    retstring = leftvalue + " " + verb + " " + rightvalue
  else :
    retstring = "(" + str(leftvalue) + " " + verb + " " + str(rightvalue) + ")"
  return retstring
