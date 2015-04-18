#! /usr/bin/env python

import sys
import os
from GtBurst import commandDefiner
from GtBurst.Configuration import Configuration
from GtBurst import getLLEfiles
from GtBurst import TriggerSelector

################ Command definition #############################
executableName                = "gtdownloadLLEdata"
version                       = "1.0.0"
shortDescription              = "Download LAT data for a trigger"
author                        = "G.Vianello, giacomov@slac.stanford.edu"
thisCommand                   = commandDefiner.Command(executableName,shortDescription,version,author)

#Define the command parameters
thisCommand.addParameter("triggername","Name for the trigger (Examples: 'bn100724029','SF120603745')",commandDefiner.MANDATORY)
thisCommand.addParameter("detlist","Detector list. Do not use if you want to download all detectors. Ex. 'n1,n2,b0'",
                                   commandDefiner.OPTIONAL,'')
thisCommand.addParameter("types","List of data type to download. Do not use if you want to download all types."+
                                  " Legal types are tte, cspec ctime. Ex. 'tte,ctime' will download only TTE and CSPEC files."+
                                  " Default is to download TTE and CSPEC (no CTIME)",
                                   commandDefiner.OPTIONAL,'tte,cspec')

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
    triggername                   = thisCommand.getParValue('triggername').replace("bn","")
    datarepository                = os.path.abspath(os.path.expanduser(thisCommand.getParValue('datarepository')))
  except KeyError as err:
    print("\n\nERROR: Parameter %s not found or incorrect! \n\n" %(err.args[0]))
    
    #Print help
    print thisCommand.getHelp()
    return
  pass
    
  configuration           = Configuration()
  
  collector               = getLLEfiles.LLEdataCollector(triggername,configuration.get('ftpWebsite'),
                                           datarepository)
  
  collector.getFTP()
  
  return ''
pass

thisCommand.run = run

if __name__=='__main__':
  thisCommand.greetings()
  #Get all key=value pairs as a dictionary
  args                           = dict(arg.split('=') for arg in sys.argv[1:])
  gtdownloadLATdata(**args)
pass
