#! /usr/bin/env python

import sys
import os
from GtBurst import commandDefiner

################ Command definition #############################
executableName                = "gtllebin"
version                       = "1.1.0"
shortDescription              = "Produce a CSPEC file with a custom time bin size using liear time bin from tstart,tsopt with a bin size of dt. OR clone the time bins from an input CSPEC file (cspec_in)."
author                        = "G.Vianello, giacomov@slac.stanford.edu"
thisCommand                   = commandDefiner.Command(executableName,shortDescription,version,author)

#Define the command parameters
thisCommand.addParameter("eventfile","Input LLE event list (LLE file)",commandDefiner.MANDATORY,partype=commandDefiner.DATASETFILE,extension="fit")
thisCommand.addParameter("rspfile","LLE response (RSP file)",commandDefiner.MANDATORY,partype=commandDefiner.DATASETFILE,extension="rsp")
thisCommand.addParameter("ft2file","Spacecraft file (FT2)",commandDefiner.MANDATORY,partype=commandDefiner.DATASETFILE,extension="fits")
thisCommand.addParameter("cspec_in","CSPEC file to USE as time bin",commandDefiner.OPTIONAL)
thisCommand.addParameter("dt","Time bin size (in seconds)",commandDefiner.OPTIONAL)
thisCommand.addParameter("tstart","Start time for the output file (seconds from trigger or MET)",commandDefiner.OPTIONAL)
thisCommand.addParameter("tstop","Stop time for the output file (seconds from trigger or MET)",commandDefiner.OPTIONAL)
thisCommand.addParameter("cspecfile","Name for the output CSPEC file",commandDefiner.MANDATORY,partype=commandDefiner.OUTPUTFILE,extension="pha")
thisCommand.addParameter("clobber","Overwrite output file? (possible values: 'yes' or 'no')",commandDefiner.OPTIONAL,"yes")
thisCommand.addParameter("verbose","Verbose output (possible values: 'yes' or 'no')",commandDefiner.OPTIONAL,"yes")

#Define the description which will be showed in the GUI
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

def gtllebin(**kwargs):
  run(**kwargs)
pass

def run(**kwargs):
  if(len(kwargs.keys())==0):
    #Nothing specified, the user needs just help!
    thisCommand.getHelp()
    return
  
  # Get parameters values
  thisCommand.setParValuesFromDictionary(kwargs)
  cspec_in                      = None
  try:
    eventfile                   = thisCommand.getParValue('eventfile')
    rspfile                     = thisCommand.getParValue('rspfile')
    ft2file                     = thisCommand.getParValue('ft2file')
    cspec_in                    = thisCommand.getParValue('cspec_in')
    dt                          = thisCommand.getParValue('dt')
    tstart                      = thisCommand.getParValue('tstart')
    tstop                       = thisCommand.getParValue('tstop')
    outfile                     = thisCommand.getParValue('cspecfile')
    clobber                     = _yesOrNoToBool(thisCommand.getParValue('clobber'))
    verbose                     = _yesOrNoToBool(thisCommand.getParValue('verbose'))
  except KeyError as err:
    print("\n\nERROR: Parameter %s not found or incorrect! \n\n" %(err.args[0]))
    
    #Print help
    print thisCommand.getHelp()
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
  tempPHA2filename            = "__gtllebin__pha2.pha"
  
  # This will use the same energy binning as in the EBOUNDS extension of the rspfile
  message("\n *  Run gtbindef and gtbin and bin in energy and time...\n")

  # if you input a cspec file it will clone the time binning:
  if cspec_in is not None:
    import pyfits
    tmpFile=pyfits.open(cspec_in)
    message('=> Copying the binning from: %s' % cspec_in)
    _SPECTRUM=tmpFile['SPECTRUM'].data
    _TIME    =_SPECTRUM.field('TIME')
    _ENDTIME =_SPECTRUM.field('ENDTIME')
    tempTimeBinFile="__tmpBinFileFromCSPEC.txt"
    txt=''
    for i in range(len(_TIME)): txt+='%s\t%s\n' %( _TIME[i],_ENDTIME[i])
    file(tempTimeBinFile,'w').writelines(txt)
    tempTimeBinFile_fits="__tmpBinFileFromCSPEC.fits"
    

    lleData.gtbindef['bintype']='T'
    lleData.gtbindef['binfile']=tempTimeBinFile
    lleData.gtbindef['outfile']=tempTimeBinFile_fits
    lleData.gtbindef.run()    

    lleData.binByEnergyAndTime(tempTimeBinFile_fits,tempPHA2filename)
  else: lleData.binByEnergyAndTime(tstart,tstop,dt,tempPHA2filename)
  
  message("\n    done.")
  
  #Transform the PHA2 in CSPEC
  message("\n *  Transform gtbin output in CSPEC format...")
  
  pha2                        = dataHandling.Spectra(tempPHA2filename)
  #Set Poisson errors to true (this will make POISSERR=True in the output CSPEC file)
  pha2.setPoisson(True)
  pha2.write(outfile,format="CSPEC",trigtime=lleData.trigTime,clobber=clobber)
  
  #Remove the temporary PHA2 file
  os.remove(tempPHA2filename)
  
  message("\n    done.")
  
  #Copy some keywords from the LLE file to the CSPEC file
  message("\n *  Updating keywords in the headers of the CSPEC file...")
  
  dataHandling.fixHeaders(eventfile,outfile)
  message("\n    done.")
  
  message("\n%s done!" %(thisCommand.name))
  
  return 'cspecfile', outfile
pass

thisCommand.run = run

if __name__=='__main__':
  thisCommand.greetings()
  #Get all key=value pairs as a dictionary
  args                           = dict(arg.split('=') for arg in sys.argv[1:])
  gtllebin(**args)
pass
