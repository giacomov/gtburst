#! /usr/bin/env python

import sys
import os

from GtBurst import commandDefiner
from GtBurst import interactivePlots
from GtBurst import dataHandling

################ Command definition #############################
executableName                = "gtllesrcbindef"
version                       = "1.0.0"
shortDescription              = "Define time intervals for extracting observed spectrum (just a wrapper around gtbindef)"
author                        = "G.Vianello, giacomov@slac.stanford.edu"
thisCommand                   = commandDefiner.Command(executableName,shortDescription,version,author)

#Define the command parameters
thisCommand.addParameter("intervals","Comma-separated definition of intervals, in seconds from trigger or MET. Ex: '10.2-20.3 , 52-132.0' or '283996802.12 - 283996802'. 'i' for interactive choice.",commandDefiner.MANDATORY,"interactive")
thisCommand.addParameter("cspecfile","Input CSPEC file",commandDefiner.OPTIONAL,partype=commandDefiner.DATASETFILE,extension="pha")
thisCommand.addParameter("eventfile","Input event file (if you want to rebin the data before choosing the interval)",commandDefiner.OPTIONAL,partype=commandDefiner.DATASETFILE,extension="fit")
thisCommand.addParameter("rspfile","Response (RSP/RSP2 file)",commandDefiner.OPTIONAL,partype=commandDefiner.DATASETFILE,extension="rsp")
thisCommand.addParameter("ft2file","Spacecraft file (FT2)",commandDefiner.OPTIONAL,partype=commandDefiner.DATASETFILE,extension="fits")
thisCommand.addParameter("dt","Desired time bin size for the rebinning",commandDefiner.OPTIONAL)
thisCommand.addParameter("tstart","Start time for the output file (seconds from trigger)",commandDefiner.OPTIONAL)
thisCommand.addParameter("tstop","Stop time for the output file (seconds from trigger)",commandDefiner.OPTIONAL)
thisCommand.addParameter("srcintervals","Name for the output bin file",commandDefiner.MANDATORY,partype=commandDefiner.OUTPUTFILE,extension='fits')
thisCommand.addParameter("clobber","Overwrite output file? (possible values: 'yes' or 'no')",commandDefiner.OPTIONAL,"yes")
thisCommand.addParameter("verbose","Verbose output (possible values: 'yes' or 'no')",commandDefiner.OPTIONAL,"yes")
thisCommand.addParameter("figure","Matplotlib figure for the interactive mode",commandDefiner.OPTIONAL,None,partype=commandDefiner.PYTHONONLY)

GUIdescription                = "In this step you have to define the time intervals you are interested into."
GUIdescription               += " If you want to, you can rebin the data by specifying a new bin size dt, and"
GUIdescription               += " the desired start and stop time of the rebinned light curve. Otherwise, leave dt, tstart and tstop to 'None'."
GUIdescription               += "TIP Insert 'i' or 'interactive' in the form to select interval(s) interactively."
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
  def __init__(self,verbose=True):
    self.verbose              = bool(verbose)
  pass
  
  def __call__(self,string):
    if(self.verbose):
      print(string)
pass   

def gtllesrcbindef(**kwargs):
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
    eventfile                   = thisCommand.getParValue('eventfile')
    rspfile                     = thisCommand.getParValue('rspfile')
    dt                          = thisCommand.getParValue('dt')
    outfile                     = thisCommand.getParValue('srcintervals')
    clobber                     = _yesOrNoToBool(thisCommand.getParValue('clobber'))
    verbose                     = _yesOrNoToBool(thisCommand.getParValue('verbose'))
  except KeyError as err:
    print("\n\nERROR: Parameter %s not found or incorrect! \n\n" %(err.args[0]))
    
    #Print help
    print thisCommand.getHelp()
    return
  pass
  
  message                     = Message(verbose)
  
  if(eventfile!=None and rspfile!=None and dt!=None
     and eventfile!='None' and rspfile!='None' and dt!='None'):
    #Run gtllebin before to rebin the TTE/LLE file and generate a custom CSPEC file
    gtllebinpar               = dict(kwargs)
    from GtBurst.commands.gtllebin import thisCommand as gtllebin
    gtllebinpar['cspecfile']  = "__temporary_cspec.fits"
    try:
      outparname, outfile       = gtllebin.run(**gtllebinpar)
      kwargs[outparname]        = outfile
    except:
      sys.stderr.write("Could not rebin data. Did you load TTE or LLE files?\n\n")
      raise
  #Just run gtllesrcbindef
  from GtBurst.commands.gtllebindef import thisCommand as gtllebindef
  kwargs['intervaltype']      = "source"
  kwargs['outfile']           = outfile
  outparname, outfile         = gtllebindef.run(**kwargs)
  
  message("\n%s done!" %(thisCommand.name))
  
  return 'srcintervals', outfile
  
pass

thisCommand.run = run

if __name__=='__main__':
  thisCommand.greetings()
  #Get all key=value pairs as a dictionary
  args                           = dict(arg.split('=') for arg in sys.argv[1:])
  gtllesrcbindef(**args)
pass

