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
#
# 
#
# Mom, Pop and Apple Pie classes, imports and functions that all files should have.
# 
#

# Improved Python3 print FUNCTION
# These need to come first to ensure that we have them available
from __future__ import print_function

# These are imports that everyone will be needing
from random import randint
import os, sys, traceback, re, time, logging, datetime

# We use this in our printfs to determine which "run" of the Python script we
# are going against. For instance, two sequential requests for the same data
# to the same "run" should yield cache hits. Annoyingly tacks an "L" when the
# value is in the LONG range. But it's just a string, so that's good enough
ourRunId=str(hex(randint(0,0xFFFFFFFF)))

def InstanceId() :
  return ourRunId

print_level = 5

def SETLEVEL(L) :
  global print_level
  print_level = int(L)

def GETLEVEL() :
  global print_level
  return print_level

def ISLEVEL(L) :
  global print_level
  return (L <= 0 or (print_level > 0 and L >= print_level))

# We have a level over-and-above INFO so that we do not have to change
# the logging level for EVERYONE. In other words, we can squelch our messages
# without squelching messages from The Google that we might want
def INFOPRINT(A,L=1) :
  global ourRunId
  global print_level
  # Ensure that logging doesn't take down the service!
  try:
    if (L <= 0 or (print_level > 0 and L >= print_level)) :
      logging.info("INSTANCE " + ourRunId + ": " + A)
  except:
    pass

def MUSTPRINT(A, actuallyCritical=False) :
  global ourRunId
  try:
    logging.critical(("(not really critical)" if not actuallyCritical else "") + 
                      "INSTANCE " + ourRunId + ": " + A)
  except:
    pass

# This class is like "None", but is used for Default values
class Default : pass

# Simple class that allows us to pass a set by reference
class SetHolder:
  def __init__(self) :
    self.setObj = set()

  def put(self, key) :
    return self.setObj.put(key)

  # Unfortunately, I can't think of a way to make "in" work without
  # saying "in ref.setObj".

# Simple class that allows us to pass a dict by reference
class DictHolder:
  def __init__(self) :
    self.dictObj = dict()

  def put(self, key, value) :
    return self.dictObj.put(key, value)

  def get(self, key, value) :
    return slf.dictObj.get(key, value)

  # Any other fancy stuff should be against the dictObj


MUSTPRINT("#####################")
MUSTPRINT("Started at " + str(datetime.datetime.now()))
MUSTPRINT("#####################")


# Performance time calculation.
# Successive calls to "printInterval" will tell you
# the time in milliseconds between the calls.

# Conv. function to get current time in milliseconds
def getMillis() :
  return int(round(time.time() * 1000))

mostRecentMillis=getMillis()

# Function for updating the current millis variable
# and printing out the time since it was last set.
def printInterval(string,L=2) :
  global mostRecentMillis
  millValley = mostRecentMillis
  mostRecentMillis = getMillis()
  interval = mostRecentMillis - millValley
  INFOPRINT("%s: %d milliseconds"%(string, interval),L)
