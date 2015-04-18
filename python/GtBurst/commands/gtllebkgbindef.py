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
executableName                = "gtllebkgbindef"
version                       = "1.0.0"
shortDescription              = "Define time intervals for the background fit (just a wrapper around gtbindef)"
author                        = "G.Vianello, giacomov@slac.stanford.edu"
thisCommand                   = commandDefiner.Command(executableName,shortDescription,version,author)

#Define the command parameters
thisCommand.addParameter("intervals","Comma-separated definition of intervals, in seconds from trigger or MET. Ex: '10.2-20.3 , 52-132.0' or '283996802.12 - 283996802'. 'i' for interactive choice.",commandDefiner.MANDATORY,"i")
thisCommand.addParameter("cspecfile","Input CSPEC file",commandDefiner.MANDATORY,partype=commandDefiner.DATASETFILE,extension="pha")
thisCommand.addParameter("bkgintervals","Name for the output bin file",commandDefiner.MANDATORY,partype=commandDefiner.OUTPUTFILE,extension="fits")
thisCommand.addParameter("clobber","Overwrite output file? (possible values: 'yes' or 'no')",commandDefiner.OPTIONAL,"yes")
thisCommand.addParameter("verbose","Verbose output (possible values: 'yes' or 'no')",commandDefiner.OPTIONAL,"yes")
thisCommand.addParameter("figure","Matplotlib figure for the interactive mode",commandDefiner.OPTIONAL,None,partype=commandDefiner.PYTHONONLY)

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

def gtllebkgbindef(**kwargs):
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
    outfile                     = thisCommand.getParValue('bkgintervals')
    clobber                     = _yesOrNoToBool(thisCommand.getParValue('clobber'))
    verbose                     = _yesOrNoToBool(thisCommand.getParValue('verbose'))
  except KeyError as err:
    print("\n\nERROR: Parameter %s not found or incorrect! \n\n" %(err.args[0]))
    
    #Print help
    print thisCommand.getHelp()
    return
  pass
  
  message                     = Message(verbose)
  
  #Just run gtllebindef
  from gtllebindef import thisCommand as gtllebindef
  kwargs['intervaltype']      = "background"
  kwargs['outfile']           = outfile
  outparname, outfile         = gtllebindef.run(**kwargs)
  
  message("\n%s done!" %(thisCommand.name))
  
  return 'bkgintervals', outfile
  
pass

thisCommand.run = run

if __name__=='__main__':
  thisCommand.greetings()
  #Get all key=value pairs as a dictionary
  args                           = dict(arg.split('=') for arg in sys.argv[1:])
  gtllebkgbindef(**args)
pass

