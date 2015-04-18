#! /usr/bin/env python

import sys
import os
import pyfits
from GtBurst import commandDefiner

################ Command definition #############################
executableName                = "gtllebkgGUI"
version                       = "1.0.0"
shortDescription              = "Fit the background with a polynomial for each channel, and return background spectra for the specified time intervals"
author                        = "G.Vianello, giacomov@slac.stanford.edu"
thisCommand                   = commandDefiner.Command(executableName,shortDescription,version,author)

#Define the command parameters
thisCommand.addParameter("intervals","Comma-separated definition of intervals, in seconds from trigger or MET. Ex: '10.2-20.3 , 52-132.0' or '283996802.12 - 283996802'. 'i' for interactive choice.",commandDefiner.MANDATORY,"interactive")
thisCommand.addParameter("cspecfile","Input CSPEC file",commandDefiner.MANDATORY,partype=commandDefiner.DATASETFILE,extension="pha")
thisCommand.addParameter("rspfile","LLE response (RSP file)",commandDefiner.MANDATORY,partype=commandDefiner.DATASETFILE,extension="rsp")
thisCommand.addParameter("bkgintervals","FITS file defining off-pulse time intervals",commandDefiner.OPTIONAL,"__bkgintervals.temp",partype=commandDefiner.OUTPUTFILE,extension="fits")
thisCommand.addParameter("srcintervals","FITS file defining source time intervals",commandDefiner.MANDATORY,partype=commandDefiner.INPUTFILE,extension="fits")
thisCommand.addParameter("bkgspectra","Name for the output file",commandDefiner.MANDATORY,partype=commandDefiner.OUTPUTFILE,extension="bak")
thisCommand.addParameter("clobber","Overwrite output file? (possible values: 'yes' or 'no')",commandDefiner.OPTIONAL,"yes")
thisCommand.addParameter("verbose","Verbose output (possible values: 'yes' or 'no')",commandDefiner.OPTIONAL,"yes")
thisCommand.addParameter("figure","Matplotlib figure for the interactive mode",commandDefiner.OPTIONAL,None,partype=commandDefiner.PYTHONONLY)

GUIdescription               = "In this step you will produce the background spectra."
GUIdescription              += " You have to select off-pulse intervals."
GUIdescription              += " The program will then fit a different polynomial for each channel of the detector,"
GUIdescription              += " and it will interpolate such polynomials in the pulse interval(s) to compute the background spectrum."  
GUIdescription              += " TIP Select two time intervals, one before and one after the pulse if you can,"
GUIdescription              += " large but without covering part of the light curve where the background is"
GUIdescription              += " highly variable."
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

def gtllebkgGUI(**kwargs):
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
    rspfile                     = thisCommand.getParValue('rspfile')
    bkgintervalsFile            = thisCommand.getParValue('bkgintervals')
    srcintervalsFile            = thisCommand.getParValue('srcintervals')
    outfile                     = thisCommand.getParValue('bkgspectra')
    figure                      = thisCommand.getParValue('figure')
    clobber                     = _yesOrNoToBool(thisCommand.getParValue('clobber'))
    verbose                     = _yesOrNoToBool(thisCommand.getParValue('verbose'))
  except KeyError as err:
    print("\n\nERROR: Parameter %s not found or incorrect! \n\n" %(err.args[0]))
    
    #Print help
    thisCommand.getHelp()
    return
  pass
  
  from gtllebkgbindef import thisCommand as gtllebkgbindef
  from gtllebkg import thisCommand as gtllebkg
  
  message                     = Message(verbose)
  while(1==1):
    #Run gtllebkgbindef
    kwargs['bkgintervals']      = bkgintervalsFile
    key, outfile                = gtllebkgbindef.run(**kwargs)
    #Run gtllebkg
    kwargs[key]                 = outfile
    key2, outfile2,cspecBackground = gtllebkg.run(**kwargs)
    message("\n%s done!" %(thisCommand.name))
    
    if(figure!=None):
      #We are in the GUI
      #Show a light curve with the residuals for the background
      cspecBackground.makeLightCurveWithResiduals(**kwargs)
      if(cspecBackground.accepted):
        print("Accepted!")
        break
      else:
        #If the user selected by hand some intervals,
        #just exit from the procedure, so that he can enter
        #them again in the GUI
        if(kwargs['intervals'][0].lower()=='i'):
          print("Ok, let's restart...")
          continue
        else:
          return None    
      pass
    else:
      #Assume everything worked
      break
  pass
  
  return key2, outfile2
pass


thisCommand.run = run

if __name__=='__main__':
  thisCommand.greetings()
  #Get all key=value pairs as a dictionary
  args                           = dict(arg.split('=') for arg in sys.argv[1:])
  gtllebkgGUI(**args)
pass
