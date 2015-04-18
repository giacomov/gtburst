#! /usr/bin/env python

import sys
import os
import matplotlib.pyplot as plt
import numpy as np
import re
from matplotlib.widgets import SpanSelector
from matplotlib.patches import Rectangle
import pyfits

from GtApp import GtApp

from GtBurst import commandDefiner
from GtBurst import interactivePlots
from GtBurst import dataHandling

################ Command definition #############################
executableName                = "gtllebindef"
version                       = "1.0.0"
shortDescription              = "Define time intervals (just a wrapper around gtbindef)"
author                        = "G.Vianello, giacomov@slac.stanford.edu"
thisCommand                   = commandDefiner.Command(executableName,shortDescription,version,author)

#Define the command parameters
thisCommand.addParameter("intervals","Comma-separated definition of intervals, in seconds from trigger or MET. Ex: '10.2-20.3 , 52-132.0' or '283996802.12 - 283996802'. 'i' for interactive choice.",commandDefiner.MANDATORY)
thisCommand.addParameter("cspecfile","Input CSPEC file",commandDefiner.MANDATORY,partype=commandDefiner.DATASETFILE,extension="pha")
thisCommand.addParameter("intervaltype","Interval type ('source' or 'background')",commandDefiner.MANDATORY,possibleValues=['source','background'])
thisCommand.addParameter("outfile","Name for the output bin file",commandDefiner.MANDATORY,partype=commandDefiner.OUTPUTFILE,extension="fits")
thisCommand.addParameter("clobber","Overwrite output file? (possible values: 'yes' or 'no')",commandDefiner.OPTIONAL,"yes")
thisCommand.addParameter("verbose","Verbose output (possible values: 'yes' or 'no')",commandDefiner.OPTIONAL,"yes")
thisCommand.addParameter("figure","Matplotlib figure for the interactive mode",commandDefiner.OPTIONAL,None,partype=commandDefiner.PYTHONONLY)

thisCommand.setGUIdescription(''' You should not see this.
''')

##################################################################

def _yesOrNoToBool(value):      
  if(value.lower()=="yes"):
    return True
  elif(value.lower()=="no"):
    return False
  else:
    raise ValueError("Unrecognized clobber option. You can use 'yes' or 'no'")    
  pass
pass

class Message(object):
  def __init__(self,verbose=True):
    self.verbose              = bool(verbose)
  pass
  
  def __call__(self,string):
    if(self.verbose):
      print(string)
pass   

def gtllebindef(**kwargs):
  run(**kwargs)
pass

def run(**kwargs):
  if(len(kwargs.keys())==0):
    #Nothing specified, the user needs just help!
    thisCommand.getHelp()
    return
  pass
  
  #Get parameters values
  thisCommand.setParValuesFromDictionary(kwargs)
  try:
    intervals                   = thisCommand.getParValue('intervals')
    cspecfile                   = thisCommand.getParValue('cspecfile')
    intervalType                = thisCommand.getParValue('intervaltype')
    outfile                     = thisCommand.getParValue('outfile')
    clobber                     = _yesOrNoToBool(thisCommand.getParValue('clobber'))
    verbose                     = _yesOrNoToBool(thisCommand.getParValue('verbose'))
    figure                      = thisCommand.getParValue('figure')
  except KeyError as err:
    print("\n\nERROR: Parameter %s not found or incorrect! \n\n" %(err.args[0]))
    
    #Print help
    print thisCommand.getHelp()
    return
  pass
  
  message                     = Message(verbose)
  
  #Load LLE data

  trigTime                    = dataHandling.getTriggerTime(cspecfile)
  
  if(intervals[0].lower()=='i'):
    message(" *  Get time intervals interactively...")
        
    if(intervalType=="background"):
      interactiveFigure           = interactivePlots.getInteractiveFigureFromCSPEC(cspecfile,selectSource=False,
                                                                                   selectBackground=True,
                                                                                   figure=figure)
      #interactiveFigure.printHelp()
      interactiveFigure.activate()
      interactiveFigure.wait()
      #Here the user has selected its intervals
      figure.clear()
      figure.canvas.draw()
      timeIntervals               = interactiveFigure.backgroundBounds
    elif(intervalType=="source"):
      interactiveFigure           = interactivePlots.getInteractiveFigureFromCSPEC(cspecfile,selectSource=True,
                                                                                   selectBackground=False,
                                                                                   figure=figure)
      #interactiveFigure.printHelp()
      interactiveFigure.activate()
      interactiveFigure.wait()
      #Here the user has selected its intervals
      figure.clear()
      figure.canvas.draw()
      timeIntervals               = interactiveFigure.sourceBounds
    pass
        
    message("\n    done.")
  else:
    intervals                     = intervals.replace(" ","")
    userBounds                    = intervals.split(",") 
    timeBounds                    = []
    for i,tt in enumerate(userBounds):
      m                           = re.search('([-,+]?[0-9]+(\.[0-9]+)?)-([-,+]?[0-9]+(\.[0-9]+)?)', tt)
      if(m!=None):
        if(m.group(1)!=None and m.group(3)!=None):
          timeBounds.append(m.group(1))
          timeBounds.append(m.group(3))
        else:
          raise ValueError("Could not understand time intervals syntax!")
      else:
        raise ValueError("Could not understand time intervals syntax!")
    pass

    timeIntervals                 = map(lambda x:float(x)+int(float(x) < 231292801.000)*trigTime,timeBounds)
  pass
  
  if(len(timeIntervals) < 2 or float(len(timeIntervals))%2 !=0):
    raise commandDefiner.UserError("No intervals selected, or not-even number of boundaries.")
  
  #Check that time intervals do not overlaps
  tstarts                     = timeIntervals[::2]
  tstops                      = timeIntervals[1::2]
  intervals                   = []
  
  for t1,t2 in zip(tstarts,tstops):
    intervals.append(dataHandling.TimeInterval(t1,t2))
  pass
  for interval1 in intervals:
    for interval2 in intervals:
      if(interval1==interval2): continue
      if(interval1.overlapsWith(interval2)):
        raise commandDefiner.UserError("Intervals MUST be non-overlapping!")
      pass
    pass
  pass
  
  #Sort
  timeIntervals.sort()
      
  message(" *  Define ASCII file with time intervals...")
  for i,t1,t2 in zip(range(len(timeIntervals[::2])),timeIntervals[::2],timeIntervals[1::2]):
    message("    Interval %s: %s - %s (%s - %s)" %(i+1,t1,t2,t1-trigTime,t2-trigTime))
  interactivePlots.writeAsciiFile(timeIntervals,"__asciiTimeBins.txt")
  message("\n    done.")
  
  message(" *  Define FITS file with time intervals...")
  
  gtbindef=GtApp('gtbindef')
  gtbindef['bintype']='T'
  gtbindef['binfile']="__asciiTimeBins.txt"
  gtbindef['outfile']=outfile
  gtbindef['clobber']='yes'
  gtbindef.run()
  
  message("\n    done.")
  
  os.remove("__asciiTimeBins.txt")
  
  message("\n%s done!" %(thisCommand.name))
  
  return 'outfile', outfile
  
pass

thisCommand.run = run

if __name__=='__main__':
  thisCommand.greetings()
  #Get all key=value pairs as a dictionary
  args                           = dict(arg.split('=') for arg in sys.argv[1:])
  gtllebindef(**args)
pass

