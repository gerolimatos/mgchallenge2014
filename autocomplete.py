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

import requests

from BaseImport import *
from soqlinterface import *

# Modified version of ternary tree implementation found at:
# http://hacktalks.blogspot.com/2012/03/implementing-auto-complete-with-ternary.html

# Each node contains 5 parts:
# self.ch => contains the character
# self.flag => Flag to Check whether the node is an end character of a valid string
# self.left, self.right => Links to the next nodes ( Working similar to Binary Search Tree)
# self.center => Link to the next valid character


# Ternary tree node. This implementation does not have a special class
# for the tree itself. You just create a node and call that the root of your
# tree
class Node:
  def __init__(self,ch='',flag=0): # Constructor for Node Object
    self.ch = ch
    self.flag = flag
    self.left = 0
    self.right = 0
    self.center = 0

  def addString(self,string) :
    # Prevent needless generation of strings
    if (ISLEVEL(1)) : INFOPRINT("ADDDING STRING \"%s\""%string,1)
    self.add(string,self)

  def add(self,string,node): # Function to add a string
    key = string[0]
    if node == 0 :
        node = Node(key,0)
    if key < node.ch :
        node.left = node.add(string,node.left)
    elif key > node.ch :
        node.right = node.add(string,node.right)
    else :
        if len(string) == 1 :
            node.flag = 1
        else : node.center = node.add(string[1:],node.center)
    return node

  def spdfs(self,match,setHolder):  # DFS for Ternary Search Tree
    if self.flag == 1 :
      setHolder.setObj.add(match)
    if self.center == 0 and self.left == 0 and self.right == 0:
      return
    if self.center != 0 :
      self.center.spdfs(match + self.center.ch, setHolder)
    if self.right != 0 :
      self.right.spdfs(match[:-1]+self.right.ch, setHolder)
    if self.left != 0 :
      self.left.spdfs(match[:-1]+self.left.ch, setHolder)

  # Function to search a string in the Ternary Search Tree
  # returns 1 if found, 0 otherwise
  def findString(self,string): 
    temp = self
    i=0
    while temp != 0 :
      if (string[i] < temp.ch) :  temp = temp.left;
      elif(string[i] > temp.ch) : temp = temp.right;
      else :
        i=i+1
        if(i == len(string)):
          return temp.flag
        temp = temp.center

    return 0


  # takes a string, 'match to date', and a SetHolder
  #  returns 1 on match
  # SetHolder is a class that must contain a set named "setObj"
  # this allows us to pass the set by reference and avoid possible
  # copying issues (although one would assume that sets are copy on write)
  def autocomplete(self,string,match,setHolder):
    # Function to implement Auto complete search

    if len(string) > 0:
      key = string[0]

      if key < self.ch :
        if(self.left == 0):
          return
        self.left.autocomplete(string,match,setHolder)

      elif key > self.ch :
        if(self.right == 0):
          return
        self.right.autocomplete(string,match,setHolder)

      else :
        if len(string) == 1:
          if self.flag == 1 : 
            setHolder.setObj.add(match+self.ch)
          if self.center != 0 :
            self.center.spdfs(match+self.ch+self.center.ch,setHolder)
          return 1
        if self.center != 0 :
          self.center.autocomplete(string[1:],match+key,setHolder)

    else :
      return

  # Takes a string to autocomplete against, returns a
  # set of matches 
  def getAutocomplete(self,string):
    setHolder = SetHolder()
    self.autocomplete(string,'',setHolder)
    return setHolder.setObj


# 
# Our table of autocomplete data.
#
class AutocompleteTable :

  def __init__(self, sname, dname) :
    self.sitename = sname
    self.datasetname = dname
    self.si = SoQLInterface(sname, dname)
    # key: lower-case title/location
    # value: correct case title/location

    # Done this way to ensure atomic switchover
    # of the dataset. Alternatively, just make a new
    # autocomplete table
    self.dataset = dict()
    self.dataset['allTitles']            = dict()
    self.dataset['allLocations']         = dict()
    self.dataset['titleAutocomplete']    = Node()
    self.dataset['locationAutocomplete'] = Node()

  # Read in the autocomplete database
  def fetchAutocomplete(self) :
    newset = dict()
    newset['allTitles']            = dict()
    newset['allLocations']         = dict()
    newset['titleAutocomplete']    = Node()
    newset['locationAutocomplete'] = Node()

    # Get the result list from the SFMOvie database
    resultlist = self.si.doGet(
              selectClause='locations,title',
              cacheExpiration=0)

    # Add title and locations
    for result in resultlist :
      t = result.get('title')
      if (t) :
        lct = t.lower()
        newset['allTitles'][lct] = t
        # Now, add in "the" removed, "a" removed, etc.
        # so that "Rock" will also match "The Rock"
        # Bug not worth fixing:
        # If there IS a "Rock" and a "The Rock", then we lose.      
        # There are no such occurances in the database
        m = re.match("(a|an|the)\s+(.*)",lct)
        if (m) :
          sublct = m.group(2)
          newset['allTitles'][sublct] = t
      loc = result.get('locations')
      if (loc) :
        lcl = loc.lower()
        newset['allLocations'][lcl] = loc
        # Now, add in "the" removed, "a" removed, etc.
        m = re.match("(a|an|the)\s+(.*)",lcl)
        if (m) :
          sublcl = m.group(2)
          newset['allLocations'][sublcl] = loc

    # Now that we have built the "the" and upper->lowercase translation table,
    # Let's start adding into the autocomplete Ternary tree itself
    for title in newset['allTitles'].keys() :
      if (title) :
        newset['titleAutocomplete'].addString(title)
    for location in newset['allLocations'].keys() :
      if (location):
        newset['locationAutocomplete'].addString(location)
    self.dataset = newset

  # Returns a dict of lists
  # locations = list
  # title = list
  def doAutocomplete(self, string) :
    retval = dict()
    # Keep us threadsafe, and keep our own ref to
    # the dataset, lest another thread refresh it
    # halfway thru our work
    dataset = self.dataset
    retval['title'] = map((lambda title: dataset['allTitles'][title]),
                  sorted(list(
                      dataset['titleAutocomplete'].getAutocomplete(string.lower()))))
    retval['locations'] = map((lambda loc: dataset['allLocations'][loc]),
                  sorted(list
                      (dataset['locationAutocomplete'].getAutocomplete(string.lower()))))
    return retval

