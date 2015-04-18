#! /usr/bin/env python

import sys
import os, shutil
from GtBurst import commandDefiner
import pyfits, numpy
from GtBurst.commands import gtdocountsmap

################ Command definition #############################
executableName                = "gtdosimulation"
version                       = "1.0.0"
shortDescription              = "Produce a siulated dataset of LAT data"
author                        = "N.Omodei, nicola.omodei@stanford.edu"
thisCommand                   = commandDefiner.Command(executableName,shortDescription,version,author)

#Define the command parameters
thisCommand.addParameter("ft2file","Spacecraft file (FT2)",commandDefiner.MANDATORY,partype=commandDefiner.DATASETFILE,extension="fits")
thisCommand.addParameter("xmlsimmodel","File of flux-style source definitions",commandDefiner.MANDATORY,partype=commandDefiner.INPUTFILE,extension="xml")
thisCommand.addParameter("srclist","File containing list of source names",commandDefiner.MANDATORY,partype=commandDefiner.DATASETFILE,extension="txt")
thisCommand.addParameter("tstart","Start time for the output file (seconds from trigger or MET)",commandDefiner.MANDATORY,0)
thisCommand.addParameter("tstop","Stop time for the output file (seconds from trigger or MET)",commandDefiner.MANDATORY,100)
thisCommand.addParameter("triggertime","Trigger time (MET)",commandDefiner.MANDATORY)
#thisCommand.addParameter("simtime","Simulation time (seconds)",commandDefiner.MANDATORY,1000)
thisCommand.addParameter("irf","Data class (TRANSIENT or SOURCE)",commandDefiner.OPTIONAL,'None',possiblevalues=['TRANSIENT','SOURCE','None'])
thisCommand.addParameter("outdir","Directory where the produced dataset will be",commandDefiner.OPTIONAL,'.')
thisCommand.addParameter("seed","Random number seed",commandDefiner.OPTIONAL,293049)
thisCommand.addParameter("simeventfile","Name for the output simulated FT1 file",commandDefiner.MANDATORY,partype=commandDefiner.OUTPUTFILE,extension="fit")
thisCommand.addParameter("figure","Matplotlib figure for the interactive mode",commandDefiner.OPTIONAL,None,partype=commandDefiner.PYTHONONLY)
thisCommand.addParameter("clobber","Overwrite output file? (possible values: 'yes' or 'no')",commandDefiner.OPTIONAL,"yes")
thisCommand.addParameter("verbose","Verbose output (possible values: 'yes' or 'no')",commandDefiner.OPTIONAL,"yes")

GUIdescription                = "With this command you simulate an observation of the LAT"
GUIdescription               += "simulate a transient observation"
GUIdescription               += "TIP After the simulation is done, you will find a new directory named"
GUIdescription               += " [trigger name]sim under the predefined data directory (usually ~/FermiData)"
GUIdescription               += ". You can load that dataset in gtburst like any other, and do analysis on it."
GUIdescription               += " Note that the simulated dataset will NOT be loaded automatically after the end"
GUIdescription               += " of the simulation."
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

def gtdosimulation(**kwargs):
  run(**kwargs)
  pass

def run(**kwargs):
  if(len(kwargs.keys())==0):
    #Nothing specified, the user needs just help!
    thisCommand.getHelp()
    return
    
  #Get parameters values
  thisCommand.setParValuesFromDictionary(kwargs)
  try:
    ft2file                     = thisCommand.getParValue('ft2file')
    infile                      = thisCommand.getParValue('xmlsimmodel')
    simeventfile                = thisCommand.getParValue('simeventfile')
    srclist                     = thisCommand.getParValue('srclist')
    tstart                      = thisCommand.getParValue('tstart')
    tstop                       = thisCommand.getParValue('tstop')
    triggertime                 = thisCommand.getParValue('triggertime')
    irf                         = thisCommand.getParValue('irf')
    seed                        = thisCommand.getParValue('seed')
    figure                      = thisCommand.getParValue('figure')
    outdir                      = thisCommand.getParValue('outdir')
    clobber                     = _yesOrNoToBool(thisCommand.getParValue('clobber'))
    verbose                     = _yesOrNoToBool(thisCommand.getParValue('verbose'))
  except KeyError as err:
    print("\n\nERROR: Parameter %s not found or incorrect! \n\n" %(err.args[0]))    
    print thisCommand.getHelp()
    return
  
  from GtBurst import dataHandling
  
  irf_                        = dataHandling._getParamFromXML(infile,'IRF')
  ra                          = dataHandling._getParamFromXML(infile,'RA')
  dec                         = dataHandling._getParamFromXML(infile,'DEC')
  name                        = dataHandling._getParamFromXML(infile,'OBJECT')
  
  if(irf_==None and irf=='None'):
    raise RuntimeError("Could not read IRF from XML file, and you did not specify it with the 'irf' command line parameter")
  
  if(irf==''):
    irf                       = irf_
  pass
    
  simtime                     = float(tstop)-float(tstart)
    
  LATSimulation               = dataHandling.Simulation(ft2file,irf,triggertime)
  outfile, idsfile            = LATSimulation.doSimulation(infile=infile,
                                srclist=srclist,
                                evroot ='__temp',
                                simtime=float(simtime),
                                tstart =float(tstart),
                                seed   =int(seed))
  
  os.rename(outfile,simeventfile)
  
  ############################
  #This happens only if the input XML has been generated by the tool in GtBurst
  if(irf_!=None and ra!=None and dec!=None and name!=None):
    try:
      #If the simeventfile follows the convention gll_ft1_tr_[triggerName]_v[version].fit
      #then produce a ft2 file which follows that too
      rootname                  = simeventfile.split("_")[3]
      version                   = simeventfile.split("_")[4]
      newft2                    = 'gll_ft2_tr_%s_%s.fit' %(rootname,version)
    except:
      #Just add a 'sim' before the extension
      rootname                  = "%ssim" % name
      atoms                     = os.path.basename(ft2file).split('.')
      newft2                    = "%ssim.%s" %(atoms[0],atoms[1])
    pass
    
    shutil.copyfile(ft2file,newft2)
    
    ft1,rsp,ft2,cspec           = dataHandling._makeDatasetsOutOfLATdata(simeventfile,newft2,rootname,
                                                                         tstart,tstop,ra,dec,triggertime,'.')
    
    if(figure!=None):
      tempfile                  = '__temp__skymap_sim.fit'
      gtdocountsmap.gtdocountsmap(eventfile=ft1,rspfile=rsp,ft2file=ft2,ra=ra,dec=dec,rad=40,
                    irf='transient',zmax=180,tstart=tstart,tstop=tstop,emin=10,
                    emax=1e9,skybinsize=0.2,skymap=tempfile,figure=figure)
      os.remove(tempfile)   
    pass
  pass
  
  #Now move them in the output directory
  if(outdir!='.'):
    destdir                   = os.path.abspath(os.path.expanduser(outdir))
    try:
      os.makedirs(destdir)
    except os.error:
      print("Note: directory %s already exists" %(outdir))
    
    for orig,dest in zip([ft1,ft2,rsp,cspec],map(lambda x:os.path.join(destdir,x),[ft1,ft2,rsp,cspec])):
      if(os.path.exists(dest)):
        if(clobber==True):
          os.remove(dest)
        else:
          raise RuntimeError("File %s already exists and clobber=no" %(dest))
        pass
      pass
      
      shutil.move(orig,dest)
      
    pass
  pass
  
  return 'simeventfile', simeventfile
pass

thisCommand.run = run

if __name__=='__main__':
  thisCommand.greetings()
  #Get all key=value pairs as a dictionary
  args                           = dict(arg.split('=') for arg in sys.argv[1:])
  gtdosimulation(**args)
  pass
