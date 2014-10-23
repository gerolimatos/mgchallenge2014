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
from __future__ import print_function

from BaseImport import *
from threading import Semaphore

import urllib

# Since our dataset is pretty small, there is no real need to make
# the cache either LRU (functools.lru_cache) or self-clearing.
# if an LRU cache is needed, use the pre-defined functools.lru_cache
# decorator in Python 3.
#
# The prevailing wisdom is that one should build a cache that allows you
# to call a function and cache its return value. I do not need to use
# that sort of functionality at this time.
# 
#

#
# Pretty braindead class that serves as a base for caches that 
# need to do tricker stuff but must remain threadsafe. Needs to
# be like this so that we can pass the cache's dict by reference
# should that ever be necessaary
#
class SimpleCache(object) :
  def __init__(self) :
    self.cache = dict()
    self.cacheid = randint(0,1000000000)

  # Looks up the URL-based value in the cache, and returns the last
  # data in the cache for that URL
  def get(self, key) :
    # get your own ref to the cache to ensure that we are threadsafe
    c = self.cache
    entry = c.get(key)
    # Why do I have to put "str" around that ternary???
    if (entry) :
      resstring = "HIT"
    else :
      resstring = "MISS"
    #INFOPRINT("SIMPLE CACHE LOOKUP FOR \"%s\": %s"%(str(key),resstring),1)
    return entry

  def put(self, key, entry) :
    c = self.cache
    #INFOPRINT("SIMPLE CACHE STORE FOR \"%s\""%(str(key),),1)
    c[key] = entry

  def clear(self):
    self.cache = dict()

  def __contains__(self, key) :
    return key in self.cache


# LRU Cache implementations are additionally NOT threadsafe, so I will
# need to put in synchronizers
# Thus, it should ONLY be used
# EXTREMELLY sparingly. In our case, we will use it for caching the
# HTTP queries from the client that we do not want to re-do
# Heavily modified form of the basic online implementation:
# (modified for readability and for "get/put" operators)
# http://stackoverflow.com/questions/4443920/python-building-a-lru-cache
#

class LRUCache (SimpleCache):

  def __init__(self, **kwargs):
    self.Parent = super(LRUCache,self)
    self.Parent.__init__()

    maxsize = kwargs.get("maxsize")
    if (not maxsize) :
      maxsize = 1024

    self.lock = Semaphore()

    # Link structure: [NEWER, OLDER, KEY, VALUE]
    # Cache entries are kept in a circular queue.
    # Root.previous is the oldest (as it cycles back)
    # Root.next is the newest
    self.root = [None, None, None, None]
    self.root[0] = self.root[1] = self.root
    self.maxsize = maxsize

  # Since get updates the cache in a very threadunfriendly way, we must
  # synchronize here. In the absense of any Python 3.x decorations, we 
  # must use a simple semaphore
  def get(self, key):
    try:
      # START CRITICAL SECTION
      self.lock.acquire(True)
      link = self.Parent.get(key)
      if (not link) :
        return None

      newer = 0
      older = 1

      # Now remove ourselves from the chain
      newerthanus, olderthanus, key, value = link
      newerthanus[older] = olderthanus
      olderthanus[newer] = newerthanus
      
      self.moveToNewestNotThreadSafe(link)
      return value

    # No except clause. If something bad happens, then yer toast
    finally:
      self.lock.release()
    # END CRITICAL SECTION

  def put(self, key, value) :
    newer = 0
    older = 1
    try:
      root = self.root
      # START CRITICAL SECTION
      self.lock.acquire(True)
      # Link structure: [PREV, NEXT, KEY, VALUE]
      if len(self.cache) >= self.maxsize:
        # This is rather strange looking: newer than root is oldest
        oldest = root[newer]
        self.removeNotThreadSafe(oldest)

      # Now insert ourselves on the head of the queue
      usedtobenewest = root[older]
      newlink = [root, usedtobenewest, key, value]

      usedtobenewest[newer] = newlink
      self.Parent.put(key, newlink)
      root[older] = newlink
      
    # No except clause: if this happens, then yer toast

    finally:
      self.lock.release()
    # END CRITICAL SECTION

  def clear(self) :
    try:
      # START CRITICAL SECTION
      self.lock.acquire(True)
      self.Parent.clear()   
      self.root[0] = self.root[1] = self.root
    except:
      pass
    finally:
      self.lock.release()
    # END CRITICAL SECTION

  def dump(self) :
    count = len(self.cache)
    root = self.root
    MUSTPRINT("LRU CACHE %d DUMP: Cache has %d items in it:"%(self.cacheid,count))
    ptr = root[1]
    i = 0
    while ptr is not root :
      MUSTPRINT("\tItem %d=%s"%(i,ptr[2]))
      ptr = ptr[1]
      i += 1
    MUSTPRINT("END OF DUMP")

  def clean(self) :
    pass

  def removeNotThreadSafe(self, link) :
    if not link:
      return
    # Can't unlink root!
    if link is self.root:
      return

    # Link structure: [NEWER, OLDER, KEY, VALUE]
    newer = 0
    older = 1

    prev = link[newer]
    next = link[older]
    # Since it's a circular list, there is no need to check null-ness
    prev[older] = next
    next[newer] = prev
    del self.cache[link[2]]

  def moveToNewestNotThreadSafe(self, link) :
    if not link:
      return
    if link is self.root:
      return
    newer = 0
    older = 1
    usedtobenewest = self.root[older]
    self.root[older] = usedtobenewest[newer] = link
    link[older] = usedtobenewest
    link[newer] = self.root



# Expiring caches are like normal caches, only they have a time to live value.
# If the cache entry is too old, it is removed and NULL is returned
# The expiration is less a matter of size than it is of age, and so items
# are only removed when they are accessed after expiration
# Note that synchronization is necessary
class ExpiringCache(SimpleCache) :

  def __init__(self, defaultExpirationSeconds):
    self.Parent = super(ExpiringCache, self)
    self.Parent.__init__()
    self.lock = Semaphore()
    self.defaultExp = defaultExpirationSeconds

  def get(self, key) :
    now = time.time()
    try:
      # START CRITICAL SECTION
      self.lock.acquire()
      value = self.Parent.get(key)
      if (not value):
        return None
      if (value['expiretime'] is not None and now >= value['expiretime']) :
        del self.Parent.cache[key]
        return None
      return value['value']
    finally:
      self.lock.release()
      # END CRITICAL SECTION


  def put(self, key, value, **kw) :
    if ('ttlseconds' in kw) :
      expirationSecs = kw[ttlseconds]
    else :
     expirationSecs = self.defaultExp
    if (expirationSecs is Default) :
      expirationSecs = self.defaultExp
    # This is a trick you can use to not put something in the cache
    if (expirationSecs is not None and expirationSecs <= 0) :
      return
    newentry = dict()
    newentry['value'] = value
    esecs = self.defaultExp if expirationSecs is None else expirationSecs 
    newentry['expiretime'] = esecs + time.time()
    try :
      # START CRITICAL SECTION
      self.lock.acquire()
      self.Parent.put(key, newentry)
    finally:
      self.lock.release()
      # END CRITICAL SECTION

  # Clean is pretty expensive, be casreful about using it
  def clean(self) :
    now = time.time()
    try:
      # START CRITICAL SECTION
      self.lock.acquire()
      for k in self.cache.keys() :
        v = self.cache.get(k)
        if v is not None:
          etime = v.get('expiretime')
          if etime is not None and etime <= now:
            del self.cache[k]
    finally:
      self.lock.release()
      # END CRITICAL SECTION

  # "in" in an expiring cache: have to see if it's in there and if the expiration time
  # is over. Note that this is not particularly threadsafe, nor does it have to be...
  # the point of "in" is to be cheap
  def __contains__(self, key) :
    value = self.cache.get(key)
    t = time.time()
    e = value['expiretime']
    #print("key=%s, value = %f, now = %f"%(str(key),e,t))

    # Expiration caches NEVER have None entries
    if value is None:
      return False

    # Check expiration
    if e <= t :
      return False

    # If we got this far, we're good to go:
    return True

  def dump(self, count = None) :
    if (not count) :
      count = len(self.cache)
      
    print("%d value, displaying the first %d keys"%(len(self.cache), count))
    i = 0
    keys = sorted(self.cache.keys())
    now = time.time()
    for key in keys:
      if i >= count :
        break
      i += 1
      print("Element %d=\"%s\" expires in %d seconds"%(i,
                                                       self.cache[key]['value'], 
                   "NEVER" if self.cache[key]['expiretime'] is None else (self.cache[key]['expiretime']-now)))



# Urlencoding happens so often that we can speed things up by caching them.
# As always, the dataset is small enough that we need not make this an LRU cache
# Thread safe enough: the worst that can happen is that url encoding will happen multiply
class UrlEncoder :
  # By having two caches, we keep the hashes 1/2 the size, and therefore possibly
  # improve hash performance with little extra cost
  decodecache = SimpleCache()
  encodecache = SimpleCache()
  @staticmethod
  def encode(str) :
    # This is a bit much. THe purpose of this was to speed up URL encoding,
    # But so many of the strings are so simple that it just doesn't matter.
    # We are probably hurting things by doing this.
    #retval = UrlEncoder.encodecache.get(str)
    #if (retval is not None) :
    #  return retval

    retval = urllib.quote_plus(str)
    #UrlEncoder.encodecache.put(str,retval)
    return retval

  @staticmethod
  def decode(str) :
    # This is a bit much. THe purpose of this was to speed up URL encoding,
    # But so many of the strings are so simple that it just doesn't matter.
    # We are probably hurting things by doing this.
    #retval = UrlEncoder.decodecache.get(str)
    #if (retval is not None) :
    #  return retval

    retval = urllib.unquote_plus(str)
    #UrlEncoder.decodecache.put(str,retval)
    return retval


import fileinput

# Main: unit test
if __name__ == '__main__':
  print("cache type? [e/l] >", end="")
  line = sys.stdin.readline()
  if ('e' in line) :
    print("Using expiring cache")
    cache = ExpiringCache(10)
  else:
    print("Using LRU cache")
    cache = LRUCache(maxsize=10)
  
  entrynum = 1
  while(True) :
    print("yes? > ", end="")
    line = sys.stdin.readline()
    line = line.strip()
    if ('d' in line) :
      print("DUMP!")
      cache.dump()
    elif ('c' in line) :
      print("CLEAN!")
      cache.clean()
      cache.dump()
    elif ('p' in line) :
      print("PUT!")
      cache.put(entrynum,1)
      print("Put %d"%entrynum)
      entrynum += 1
    elif ('i' in line):
      location = line.index('i')
      substr = line[location+1:]
      i = int(substr)
      if i in cache :
        print("Yes, %d's there, supposedly!"%i)
      else :
        print("No %d is not there ,supposedly!"%i)
    else :
      num = int(line)
      print("line=\"%s\""%num)
      if (cache.get(num) ) :
        print("found entry %d!"%num)
      else :
        print("Could not find %d"%num)
