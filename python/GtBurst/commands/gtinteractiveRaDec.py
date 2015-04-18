#! /usr/bin/env python

import sys
import os
from GtBurst import commandDefiner
import pyfits, numpy

################ Command definition #############################
executableName                = "gtinteractiveRaDec"
version                       = "1.0.0"
shortDescription              = "Produce a counts map of LAT data"
author                        = "G.Vianello, giacomov@slac.stanford.edu"
thisCommand                   = commandDefiner.Command(executableName,shortDescription,version,author)

#Define the command parameters
thisCommand.addParameter("filteredeventfile","Input event list (FT1 file)",commandDefiner.MANDATORY,partype=commandDefiner.DATASETFILE,extension="fit")
thisCommand.addParameter("skymap","Name for the output file for the sky map",commandDefiner.MANDATORY,partype=commandDefiner.DATASETFILE,extension="fit")
thisCommand.addParameter("figure","Matplotlib figure for the interactive mode",commandDefiner.OPTIONAL,None,partype=commandDefiner.PYTHONONLY)

GUIdescription                = "Click on a point in the figure to select the corresponding R.A. and Dec. for"
GUIdescription               += " re-centering the ROI"
GUIdescription               += "TIP If you are not happy with your choice, just click Run again and retry."
thisCommand.setGUIdescription(GUIdescription)

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
  def __init__(self,verbose):
    self.verbose              = bool(verbose)
  pass
  
  def __call__(self,string):
    if(self.verbose):
      print(string)
pass   

def gtinteractiveRaDec(**kwargs):
  run(**kwargs)
pass

#This will keep the ID for the callback who allow to select a photons
#in the Energy Vs Time plot and circle it in the image
callbackID                    = None

def run(**kwargs):
  if(len(kwargs.keys())==0):
    #Nothing specified, the user needs just help!
    thisCommand.getHelp()
    return
  pass
  
  #Get parameters values
  thisCommand.setParValuesFromDictionary(kwargs)
  try:
    filteredeventfile           = thisCommand.getParValue('filteredeventfile')
    skymap                      = thisCommand.getParValue('skymap')
    figure                      = thisCommand.getParValue('figure')
  except KeyError as err:
    print("\n\nERROR: Parameter %s not found or incorrect! \n\n" %(err.args[0]))
    
    #Print help
    print thisCommand.getHelp()
    return
  pass
  from GtBurst.InteractiveFt1Display import InteractiveFt1Display
  
  displ                     = InteractiveFt1Display(filteredeventfile,skymap,figure)
  displ.waitClick()
  print("\nSelected (R.A., Dec): (%s,%s)" %(displ.user_ra,displ.user_dec))
  user_ra                   = float(displ.user_ra)
  user_dec                  = float(displ.user_dec)
  displ.unbind()
  
  return 'user_ra', user_ra, 'user_dec', user_dec
pass

thisCommand.run = run

if __name__=='__main__':
  thisCommand.greetings()
  #Get all key=value pairs as a dictionary
  args                           = dict(arg.split('=') for arg in sys.argv[1:])
  gtinteractiveRaDec(**args)
pass
