#! /usr/bin/env python

import sys
import os
from GtBurst import commandDefiner

################ Command definition #############################
executableName                = "gtllesrc"
version                       = "1.0.0"
shortDescription              = "Get the observed spectra in the given time intervals (and compute the response)"
author                        = "G.Vianello, giacomov@slac.stanford.edu"
thisCommand                   = commandDefiner.Command(executableName,shortDescription,version,author)

#Define the command parameters
thisCommand.addParameter("eventfile","Input file (either TTE/LLE or CSPEC)",commandDefiner.MANDATORY,partype=commandDefiner.DATASETFILE,extension="fit")
thisCommand.addParameter("rspfile","LLE response (RSP file)",commandDefiner.MANDATORY,partype=commandDefiner.DATASETFILE,extension="rsp")
thisCommand.addParameter("ft2file","Spacecraft file (FT2)",commandDefiner.OPTIONAL,"None",partype=commandDefiner.DATASETFILE,extension="fits")
thisCommand.addParameter("srcintervals","FITS file defining source time intervals",commandDefiner.MANDATORY,partype=commandDefiner.INPUTFILE,extension="fits")
thisCommand.addParameter("srcspectra","Name for the output PHA file",commandDefiner.MANDATORY,partype=commandDefiner.OUTPUTFILE,extension="pha")
thisCommand.addParameter("weightedrsp","Name for the output RSP file",commandDefiner.MANDATORY,partype=commandDefiner.OUTPUTFILE,extension="rsp")
thisCommand.addParameter("clobber","Overwrite output file? (possible values: 'yes' or 'no')",commandDefiner.OPTIONAL,"yes")
thisCommand.addParameter("verbose","Verbose output (possible values: 'yes' or 'no')",commandDefiner.OPTIONAL,"yes")

GUIdescription                = "In this step the program will bin the data to produce the observed spectrum"
GUIdescription               += " for the time intervals you previously selected."

thisCommand.setGUIdescription(GUIdescription)
##################################################################

executableName                = "gtllesrc v 1.0.0"
authorString                  = "G.Vianello, giacomov@slac.stanford.edu"

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

def gtllesrc(**kwargs):
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
    eventfile                   = thisCommand.getParValue('eventfile')
    rspfile                     = thisCommand.getParValue('rspfile')
    ft2file                     = thisCommand.getParValue('ft2file')
    srcintervals                = thisCommand.getParValue('srcintervals')
    outfile                     = thisCommand.getParValue('srcspectra')
    weightedrsp                 = thisCommand.getParValue('weightedrsp')
    clobber                     = _yesOrNoToBool(thisCommand.getParValue('clobber'))
    verbose                     = _yesOrNoToBool(thisCommand.getParValue('verbose'))
  except KeyError as err:
    print("\n\nERROR: Parameter %s not found or incorrect! \n\n" %(err.args[0]))
    
    #Print help
    thisCommand.getHelp()
    return
  pass
  
  #I import this here to save time if the user makes error in the command line
  from GtBurst import dataHandling
  
  message                     = Message(verbose)
  
  #Load LLE data
  message(" *  Get energy binning from the response matrix...")
  
  lleData                     = dataHandling.LLEData(eventfile,rspfile,ft2file)
  
  message("\n    done.")
  
  #Make PHA2 with gtbin
  
  #This will use the same energy binning as in the EBOUNDS extension of the rspfile
  message("\n *  Run gtbindef and gtbin and bin in energy and time...\n")
  
  lleData.binByEnergyAndTime(srcintervals,outfile)
  message("\n    done.")
  
  #Copy some keywords from the LLE file to the PHA file
  message("\n *  Updating keywords in the headers of the PHA file...")
  
  if(lleData.isTTE):
    dataHandling.fixHeaders(eventfile,outfile)
  else:
    dataHandling.fixHeaders(eventfile,outfile,"SPECTRUM")
  message("\n    done.")
  
  message("\n *  Computing the response matrix for each interval by weighting the input matrices...")
  from GtBurst import RSPweight
  triggerTime                 = dataHandling.getTriggerTime(eventfile)
  RSPweight.RSPweight(eventfile=eventfile,timeBinsFile=srcintervals,
                      rsp2file=rspfile,outfile=os.path.abspath(weightedrsp),triggerTime=triggerTime)
  message("\n *  done.")
  
  message("\n%s done!" %(thisCommand.name))
  
  return 'srcspectra', outfile, 'weightedrsp', weightedrsp
pass

thisCommand.run = run

if __name__=='__main__':
  thisCommand.greetings()
  #Get all key=value pairs as a dictionary
  args                           = dict(arg.split('=') for arg in sys.argv[1:])
  gtllesrc(**args)
pass
