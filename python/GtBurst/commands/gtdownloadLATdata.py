#! /usr/bin/env python

import sys
import os
from GtBurst import commandDefiner
from GtBurst.Configuration import Configuration
from GtBurst import downloadTransientData
from GtBurst import TriggerSelector

################ Command definition #############################
executableName                = "gtdownloadLATdata"
version                       = "1.0.0"
shortDescription              = "Download LAT data for a trigger"
author                        = "G.Vianello, giacomov@slac.stanford.edu"
thisCommand                   = commandDefiner.Command(executableName,shortDescription,version,author)

#Define the command parameters
thisCommand.addParameter("triggername","Name for the trigger (Examples: 'bn100724029','SF120603745')",commandDefiner.MANDATORY)
thisCommand.addParameter("triggertime","Trigger time in MET (if you want to override the value in the trigger catalog)",commandDefiner.OPTIONAL,-999)
thisCommand.addParameter("ra","R.A. (if you want to override the value in the trigger catalog)",commandDefiner.OPTIONAL,-999)
thisCommand.addParameter("dec","Dec. (if you want to override the value in the trigger catalog)",commandDefiner.OPTIONAL,-999)
thisCommand.addParameter("radius","Radius of the circular Region Of Interest (ROI)",commandDefiner.OPTIONAL,60.0)
thisCommand.addParameter("timebefore","Start time (s relative from the trigger). Example: -100",commandDefiner.OPTIONAL,-100)
thisCommand.addParameter("timeafter","Stop time (s relative from the trigger). Example: 10000",commandDefiner.OPTIONAL,10000)
thisCommand.addParameter("datarepository","Where to store the files",commandDefiner.OPTIONAL,Configuration().get('dataRepository'))

GUIdescription                = "The GUI has its own system to download data"
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

def gtdownloadLATdata(**kwargs):
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
    triggername                   = thisCommand.getParValue('triggername')
    triggertime                   = float(thisCommand.getParValue('triggertime'))
    ra                            = float(thisCommand.getParValue('ra'))
    dec                           = float(thisCommand.getParValue('dec'))
    radius                        = float(thisCommand.getParValue('radius'))
    timebefore                    = float(thisCommand.getParValue('timebefore'))
    timeafter                     = float(thisCommand.getParValue('timeafter'))
    datarepository                = os.path.abspath(os.path.expanduser(thisCommand.getParValue('datarepository')))
  except KeyError as err:
    print("\n\nERROR: Parameter %s not found or incorrect! \n\n" %(err.args[0]))
    
    #Print help
    print thisCommand.getHelp()
    return
  pass
    
  configuration           = Configuration()
  
  #See if we need to download anything from the trigger catalog
  if(ra==-999 or dec==-999 or triggertime==-999):
    print("Downloading information about trigger %s from the HEASARC database..." %(triggername))
    ts                    = TriggerSelector.TriggerSelector()
    ts.done(triggername)
    if(ra==-999):
      ra                  = float(ts.ra)
    if(dec==-999):
      dec                 = float(ts.dec)
    if(triggertime==-999):
      triggertime         = float(ts.triggerTime)
  pass
  
  LATdownloader           = downloadTransientData.DownloadTransientData(triggername,configuration.get('ftpWebsite'),
                                                           datarepository)
  try:
    LATdownloader.setCuts(ra,dec,radius,triggertime,triggertime+timebefore,triggertime+timeafter,'MET')
    LATdownloader.getFTP()
  except:
    raise RuntimeError("Could not download data for trigger %s. Reason:\n\n '%s' \n\n." %(triggername,sys.exc_info()[1]))
    
  return ''
pass

thisCommand.run = run

if __name__=='__main__':
  thisCommand.greetings()
  #Get all key=value pairs as a dictionary
  args                           = dict(arg.split('=') for arg in sys.argv[1:])
  gtdownloadLATdata(**args)
pass
