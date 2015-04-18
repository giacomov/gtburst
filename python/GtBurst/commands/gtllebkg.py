#! /usr/bin/env python

import sys
import os
import pyfits
from GtBurst import commandDefiner

################ Command definition #############################
executableName                = "gtllebkg"
version                       = "1.0.0"
shortDescription              = "Fit the background with a polynomial for each channel, and return background spectra for the specified time intervals"
author                        = "G.Vianello, giacomov@slac.stanford.edu"
thisCommand                   = commandDefiner.Command(executableName,shortDescription,version,author)

#Define the command parameters
thisCommand.addParameter("cspecfile","Input CSPEC file",commandDefiner.MANDATORY,partype=commandDefiner.DATASETFILE,extension="pha")
thisCommand.addParameter("rspfile","LLE response (RSP file)",commandDefiner.MANDATORY,partype=commandDefiner.DATASETFILE,extension="rsp")
thisCommand.addParameter("bkgintervals","FITS file defining off-pulse time intervals",commandDefiner.MANDATORY,partype=commandDefiner.INPUTFILE,extension="fits")
thisCommand.addParameter("srcintervals","FITS file defining source time intervals",commandDefiner.MANDATORY,partype=commandDefiner.INPUTFILE,extension="fits")
thisCommand.addParameter("bkgspectra","Name for the output file",commandDefiner.MANDATORY,partype=commandDefiner.OUTPUTFILE,extension="bak")
thisCommand.addParameter("clobber","Overwrite output file? (possible values: 'yes' or 'no')",commandDefiner.OPTIONAL,"yes")
thisCommand.addParameter("verbose","Verbose output (possible values: 'yes' or 'no')",commandDefiner.OPTIONAL,"yes")

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
  def __init__(self,verbose):
    self.verbose              = bool(verbose)
  pass
  
  def __call__(self,string):
    if(self.verbose):
      print(string)
pass   

def gtllebkg(**kwargs):
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
    cspecfile                   = thisCommand.getParValue('cspecfile')
    rspfile                     = thisCommand.getParValue('rspfile')
    bkgintervalsFile            = thisCommand.getParValue('bkgintervals')
    srcintervalsFile            = thisCommand.getParValue('srcintervals')
    outfile                     = thisCommand.getParValue('bkgspectra')
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
  
  message                       = Message(verbose)
  
  #Load LLE data
  
  trigTime                      = dataHandling.getTriggerTime(cspecfile)
  
  message(" *  Reading background and source time intervals...")
  
  bkgIntervalsObj               = dataHandling.TimeIntervalFitsFile(bkgintervalsFile,trigTime)
  bkgIntervals                  = bkgIntervalsObj.getIntervals()
  srcIntervalsObj               = dataHandling.TimeIntervalFitsFile(srcintervalsFile,trigTime)
  srcIntervals                  = srcIntervalsObj.getIntervals()
  
  message("\n    Using bkg. time intervals:")
  if(verbose):
    print(bkgIntervalsObj)
  
  message("\n    Using src. time intervals:")
  if(verbose):
    print(srcIntervalsObj)
  
  message("\n    done.")
  
  message(" *  Fit background with polynomials...")
  
  cspecBackground               = dataHandling.CspecBackground(cspecfile,rspfile)
  backPha                       = cspecBackground.getBackgroudSpectrum(bkgIntervals,srcIntervals)
  message("\n    done.")
    
  #This will use the same energy binning as in the EBOUNDS extension of the rspfile
  message("\n *  Saving the background spectra in a PHA2 file...\n")
  
  backPha.write(outfile,format="PHA2",clobber=clobber)
  
  message("\n    done.")
    
  #Copy some keywords from the LLE file to the CSPEC file
  message("\n *  Updating keywords in the headers of the PHA2 file...")
  
  dataHandling.fixHeaders(cspecfile,outfile,"SPECTRUM")
  message("\n    done.")
  
  message("\n%s done!" %(thisCommand.name))
  
  return 'bkgspectra', outfile, cspecBackground
pass

thisCommand.run = run

if __name__=='__main__':
  thisCommand.greetings()
  #Get all key=value pairs as a dictionary
  args                           = dict(arg.split('=') for arg in sys.argv[1:])
  gtllebkg(**args)
pass
