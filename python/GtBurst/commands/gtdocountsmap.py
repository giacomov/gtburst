#! /usr/bin/env python

import sys
import os
from GtBurst import commandDefiner
from GtBurst import IRFS
from GtBurst.GtBurstException import GtBurstException
import pyfits, numpy

################ Command definition #############################
executableName                = "gtdocountsmap"
version                       = "1.0.0"
shortDescription              = "Produce a counts map of LAT data"
author                        = "G.Vianello, giacomov@slac.stanford.edu"
thisCommand                   = commandDefiner.Command(executableName,shortDescription,version,author)

#Define the command parameters
thisCommand.addParameter("eventfile","Input event list (FT1 file)",commandDefiner.MANDATORY,partype=commandDefiner.DATASETFILE,extension="fit")
thisCommand.addParameter("rspfile","LAT response (RSP file)",commandDefiner.MANDATORY,partype=commandDefiner.DATASETFILE,extension="rsp")
thisCommand.addParameter("ft2file","Spacecraft file (FT2)",commandDefiner.MANDATORY,partype=commandDefiner.DATASETFILE,extension="fits")
thisCommand.addParameter("ra","R.A. of the center of the Region of Interest (ROI) (J2000, deg)",commandDefiner.MANDATORY)
thisCommand.addParameter("dec","Dec of the center of the Region of Interest (ROI) (J2000, deg)",commandDefiner.MANDATORY)
thisCommand.addParameter("rad","Radius of the Region of Interest (ROI) (deg)",commandDefiner.MANDATORY,12)
thisCommand.addParameter("irf","Data class (TRANSIENT or SOURCE)",commandDefiner.MANDATORY,'TRANSIENT',possiblevalues=IRFS.IRFS.keys())
thisCommand.addParameter("zmax","Zenith cut in deg. If strategy==time, then time intervals when the edge of the ROI exceed this limit will be excluded from the analysis. If strategy==events, events with a Zenith angle larger than this will be excluded from the analysis.",commandDefiner.MANDATORY,100)
thisCommand.addParameter("tstart","Start time for the output file (seconds from trigger or MET)",commandDefiner.MANDATORY,0)
thisCommand.addParameter("tstop","Stop time for the output file (seconds from trigger or MET)",commandDefiner.MANDATORY,100)
thisCommand.addParameter("emin","Minimum energy (MeV) (event with a lower energy will be filtered out)",commandDefiner.MANDATORY,100)
thisCommand.addParameter("emax","Maximum energy (MeV) (event with a higher energy will be filtered out)",commandDefiner.MANDATORY,100000)
thisCommand.addParameter("skybinsize","Bin size for the sky image (deg)",commandDefiner.OPTIONAL,0.2)
thisCommand.addParameter("skymap","Name for the output file for the sky map",commandDefiner.MANDATORY,partype=commandDefiner.OUTPUTFILE,extension="fit")
thisCommand.addParameter("thetamax","Maximum theta angle for the source",commandDefiner.OPTIONAL,180.0)
thisCommand.addParameter("clobber","Overwrite output file? (possible values: 'yes' or 'no')",commandDefiner.OPTIONAL,"yes")
thisCommand.addParameter("strategy","Strategy for Zenith cut. (possible values: 'time' or 'events')",commandDefiner.OPTIONAL,"time",possibleValues=["time","events"])
thisCommand.addParameter("allowEmpty","Allow empty output (possible values: 'yes' or 'no')",commandDefiner.OPTIONAL,'no',partype=commandDefiner.HIDDEN)
thisCommand.addParameter("verbose","Verbose output (possible values: 'yes' or 'no')",commandDefiner.OPTIONAL,"yes")
thisCommand.addParameter("figure","Matplotlib figure for the interactive mode",commandDefiner.OPTIONAL,None,partype=commandDefiner.PYTHONONLY)

GUIdescription                = "Here you apply cuts on the data."
GUIdescription               += "TIP For intervals shorter than 100 s it is usually best to use TRANSIENT class, while for longer"
GUIdescription               += " intervals it is best to use the cleaner SOURCE class."
GUIdescription               += " You can use the function 'Make navigation plots' in the Tools menu to decide"
GUIdescription               += " which Zenith cut it is best to apply. Remember that all time intervals for which even a part of"
GUIdescription               += " the ROI has a Zenith angle larger than your threshold will be excluded from the analysis."
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

def gtdocountsmap(**kwargs):
  run(**kwargs)
pass

#This will keep the display class so that it is possible
#to call this command from the GUI without incurring in strange
#things caused by bindings to methods from the run before
lastDisplay                   = None

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
    ra                          = thisCommand.getParValue('ra')
    dec                         = thisCommand.getParValue('dec')
    rad                         = thisCommand.getParValue('rad')
    irf                         = thisCommand.getParValue('irf')
    zmax                        = thisCommand.getParValue('zmax')
    tstart                      = thisCommand.getParValue('tstart')
    tstop                       = thisCommand.getParValue('tstop')
    emin                        = thisCommand.getParValue('emin')
    emax                        = thisCommand.getParValue('emax')
    skybinsize                  = thisCommand.getParValue('skybinsize')    
    outfile                     = thisCommand.getParValue('skymap')
    strategy                    = thisCommand.getParValue('strategy')
    thetamax                    = float(thisCommand.getParValue('thetamax'))
    allowEmpty                  = _yesOrNoToBool(thisCommand.getParValue('allowEmpty'))
    clobber                     = _yesOrNoToBool(thisCommand.getParValue('clobber'))
    verbose                     = _yesOrNoToBool(thisCommand.getParValue('verbose'))
    figure                      = thisCommand.getParValue('figure')
  except KeyError as err:
    print("\n\nERROR: Parameter %s not found or incorrect! \n\n" %(err.args[0]))
    
    #Print help
    print thisCommand.getHelp()
    return
  pass
  
  from GtBurst import dataHandling
  global lastDisplay
  
  LATdata                     = dataHandling.LATData(eventfile,rspfile,ft2file)
  
  if(strategy.lower()=="time"):
    #gtmktime cut
    filteredFile,nEvents      = LATdata.performStandardCut(ra,dec,rad,irf,tstart,tstop,emin,emax,zmax,thetamax,True,strategy='time')
  elif(strategy.lower()=="events"):
    #no gtmktime cut, Zenith cut applied directly to the events
    filteredFile,nEvents      = LATdata.performStandardCut(ra,dec,rad,irf,tstart,tstop,emin,emax,zmax,thetamax,True,strategy='events')
  pass
  
  LATdata.doSkyMap(outfile,skybinsize)
    
  #Now open the output file and get exposure and total number of events
  skymap                      = pyfits.open(outfile)
  totalNumberOfEvents         = numpy.sum(skymap[0].data)
  totalTime                   = numpy.sum(skymap['GTI'].data.field('STOP')-skymap['GTI'].data.field('START'))
  skymap.close()
  print("\nTotal number of events in the counts map: %s" %(totalNumberOfEvents))
  print("Total time in Good Time Intervals:        %s" %(totalTime))
  if((totalTime==0) and allowEmpty==False):
    raise GtBurstException(2,"Your filter resulted in zero exposure. \n\n" +
                             " Loose your cuts, or enlarge the time interval. You might want to "+
                             " check also the navigation plots (in the Tools menu) to make sure "+
                             " that the ROI is within the LAT FOV in the desired time interval.")
  
  displ                       = None
    
  if(figure!=None):     
    if(lastDisplay!=None):
      lastDisplay.unbind()
    pass
    from GtBurst.InteractiveFt1Display import InteractiveFt1Display
    lastDisplay               = InteractiveFt1Display(filteredFile,outfile,figure,ra,dec)
  pass  
  
  return 'skymap', outfile, 'filteredeventfile', filteredFile, 'irf', irf, 'eventDisplay', lastDisplay
pass

thisCommand.run = run

if __name__=='__main__':
  thisCommand.greetings()
  #Get all key=value pairs as a dictionary
  args                           = dict(arg.split('=') for arg in sys.argv[1:])
  gtdocountsmap(**args)
pass
