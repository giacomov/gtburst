#! /usr/bin/env python

import sys
import os
from GtBurst import commandDefiner
from GtBurst import LikelihoodComponent
from GtBurst.GtBurstException import GtBurstException
import pyfits, numpy,math
import scipy.integrate
import re
import xml.etree.ElementTree as ET

################ Command definition #############################
executableName                = "gtdosed"
version                       = "1.0.0"
shortDescription              = "Build a Spectral Energy Distribution by doing energy-resolved likelihood fit"
author                        = "G.Vianello, giacomov@slac.stanford.edu"
thisCommand                   = commandDefiner.Command(executableName,shortDescription,version,author)

#Define the command parameters
thisCommand.addParameter("filteredeventfile","Input event list (FT1 file)",commandDefiner.MANDATORY,partype=commandDefiner.DATASETFILE,extension="fit")
thisCommand.addParameter("rspfile","LAT response (RSP file)",commandDefiner.MANDATORY,partype=commandDefiner.DATASETFILE,extension="rsp")
thisCommand.addParameter("ft2file","Spacecraft file (FT2)",commandDefiner.MANDATORY,partype=commandDefiner.DATASETFILE,extension="fits")
thisCommand.addParameter("tsmin","Minimum TS for each bin of the SED",commandDefiner.MANDATORY,16)
thisCommand.addParameter("fixphindex","Fix the photon index to the given value. Set this to 'prefit' if you want to use the value obtained by fitting the whole energy range. Set it to 'no' if you want to keep it free in each energy interval",commandDefiner.OPTIONAL,"prefit")
thisCommand.addParameter("expomap","pre-computed exposure map",commandDefiner.OPTIONAL,partype=commandDefiner.DATASETFILE,extension="fits")
thisCommand.addParameter("ltcube","pre-computed livetime cube",commandDefiner.OPTIONAL,partype=commandDefiner.DATASETFILE,extension="fits")
thisCommand.addParameter("xmlmodel","XML model",commandDefiner.MANDATORY,partype=commandDefiner.DATASETFILE,extension="fits")
thisCommand.addParameter("sedtxt","Text file for the output",commandDefiner.MANDATORY,partype=commandDefiner.OUTPUTFILE,extension="txt")
thisCommand.addParameter("energybins","Comma-separated list of bin boundaries (in MeV). Do not use this if you want the tool to choose the bin automatically",commandDefiner.OPTIONAL)
#thisCommand.addParameter("irf","Data class (TRANSIENT or SOURCE)",commandDefiner.MANDATORY,'TRANSIENT',possiblevalues=['TRANSIENT','SOURCE'])
thisCommand.addParameter("clobber","Overwrite output file? (possible values: 'yes' or 'no')",commandDefiner.OPTIONAL,"yes")
thisCommand.addParameter("verbose","Verbose output (possible values: 'yes' or 'no')",commandDefiner.OPTIONAL,"yes")
thisCommand.addParameter("figure","Matplotlib figure for the interactive mode",commandDefiner.OPTIONAL,None,partype=commandDefiner.PYTHONONLY)

GUIdescription                = "Here you will perform an unbinned likelihood analysis on the data you selected in the first step,"
GUIdescription               += " using the model you selected in the 2nd step."
GUIdescription               += "TIP The likelihood analysis should take between 5 and 10 minutes to complete."
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

def gtdosed(**kwargs):
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
    eventfile                   = thisCommand.getParValue('filteredeventfile')
    rspfile                     = thisCommand.getParValue('rspfile')
    ft2file                     = thisCommand.getParValue('ft2file')
    tsmin                       = float(thisCommand.getParValue('tsmin'))
    fixphindex                  = thisCommand.getParValue('fixphindex')
    expomap                     = thisCommand.getParValue('expomap')
    ltcube                      = thisCommand.getParValue('ltcube')
    xmlmodel                    = thisCommand.getParValue('xmlmodel')
    sedtxt                      = thisCommand.getParValue('sedtxt')
    energybins                  = thisCommand.getParValue('energybins')
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
  from GtBurst.angularDistance import getAngularDistance
  
  LATdata                     = dataHandling.LATData(eventfile,rspfile,ft2file)
  
  try:
    outfilelike, sources        = LATdata.doUnbinnedLikelihoodAnalysis(xmlmodel,tsmin=20,expomap=expomap,ltcube=ltcube)
  except GtBurstException as gt:
    raise gt
  except:
    raise
    
  #Now produce a pha1 file (just to compute the total exposure)
  pha1file                    = LATdata.binByEnergy(2)
  
  totalExposure               = pyfits.getheader(pha1file,'SPECTRUM').get("EXPOSURE")
  
  print("\nTotal exposure: %s s" %(totalExposure))
  
  #Transfer information on the source from the input to the output XML
  irf                         = dataHandling._getParamFromXML(xmlmodel,'IRF')
  ra                          = dataHandling._getParamFromXML(xmlmodel,'RA')
  dec                         = dataHandling._getParamFromXML(xmlmodel,'DEC')
  sourceName                  = dataHandling._getParamFromXML(xmlmodel,'OBJECT')
  
  if(irf==None):
    print("\n\nWARNING: could not read IRF from XML file. Be sure you know what you are doing...")
  else:
    dataHandling._writeParamIntoXML(outfilelike,IRF=irf,OBJECT=sourceName,RA=ra,DEC=dec)
  pass
    
  #Make a copy of the output XML file and freeze all parameters except the source
  tree                        = ET.parse(outfilelike)
  root                        = tree.getroot()
  phIndex                     = -2.0
  for source in root.findall('source'):
    if(source.get('name')!=sourceName):
      #Freeze all parameters
      for spectrum in source.findall('spectrum'):
        for param in spectrum.findall('parameter'):
          param.set('free',"%s" % 0)
        pass
      pass
    else:
      if(fixphindex.lower()!='no' and fixphindex!=False):
        #Fix photon index
        for spectrum in source.findall('spectrum'):
          for param in spectrum.findall('parameter'):
            if(param.get('name')=='Index'):
              if(fixphindex.lower()!='prefit'):
                try:
                  value           = float(fixphindex)
                except:
                  raise ValueError("The value for the photon index (%s) is not a float. Value not recognized." % fixphindex)
                print("\n\nFixing photon index to the provided value (%s) \n\n" %(value))
                param.set('value',"%s" % value)
              else:
                print("\n\nFixing photon index to the best fit value on the whole energy range\n\n")
              param.set('free',"%s" % 0)
              phIndex           = float(param.get('value'))
          pass
        pass
      pass
  pass
  f                           = open("__temporary_XML.xml",'w+')
  tree.write(f)
  f.write('''<!-- OBJECT=%s -->
<!-- DEC=%s -->
<!-- RA=%s -->
<!-- IRF=%s -->\n''' %(sourceName,ra,dec,irf))
  f.close()  
  
  
  
  #Now for each energy band, make a likelihood and compute the flux
  f                           = pyfits.open(eventfile)
  
  #Take the list in inverse order so I will rebin at low energies, instead that at high energies
  energies                    = numpy.array(sorted(f['EVENTS'].data.ENERGY)[::-1])
  totalInputCounts            = len(energies)
  f.close()
  
  if(energybins!=None):
    energyBoundaries            = map(lambda x:float(x),energybins.split(','))
  else:
    energyBoundaries          = LikelihoodComponent.optimizeBins(LATdata.like1,energies,sourceName,minTs=tsmin,minEvt=3)
  
  print("\nEnergy boundaries:")
  for i,ee1,ee2 in zip(range(len(energyBoundaries)-1),energyBoundaries[:-1],energyBoundaries[1:]):
    print("%02i: %10s - %10s" %(i+1,ee1,ee2))
  pass
  print("\n")
  print("\nNumber of energy bins: %s\n" %(len(energyBoundaries)-1))
    
  fluxes                      = numpy.zeros(len(energyBoundaries)-1)
  fluxes_errors               = numpy.zeros(len(energyBoundaries)-1)
  phfluxes                    = numpy.zeros(len(energyBoundaries)-1)
  phfluxes_errors             = numpy.zeros(len(energyBoundaries)-1)
  TSs                         = numpy.zeros(len(energyBoundaries)-1)
  phIndexes                   = numpy.zeros(len(energyBoundaries)-1)
  totalCounts                 = 0
  for i,e1,e2 in zip(range(len(fluxes)),energyBoundaries[:-1],energyBoundaries[1:]):
    thisLATdata               = dataHandling.LATData(eventfile,rspfile,ft2file,root="SED_%s-%s" %(e1,e2))
    #Further cut in the energy range for this Band
    #Remove the version _vv from the name of the irf
    cleanedIrf                = "_".join(LATdata.irf.split("_")[:-1])
    outf,thisCounts           = thisLATdata.performStandardCut(LATdata.ra,LATdata.dec,LATdata.rad,cleanedIrf,
                                                               LATdata.tmin,LATdata.tmax,e1,e2,180,gtmktime=False,roicut=False)
    totalCounts              += thisCounts
    #Perform the likelihood analysis
    outfilelike, sources      = thisLATdata.doUnbinnedLikelihoodAnalysis("__temporary_XML.xml",
                                                                         tsmin=tsmin,
                                                                         dogtdiffrsp=False,
                                                                         expomap=expomap,
                                                                         ltcube=ltcube)
    source                    = filter(lambda x:x.name==sourceName,sources)[0]
    if(source.flux.find("<")>=0):
      #This is an upper limit
      source.flux             = float(source.flux.split("<")[1].strip())
      source.fluxError        = -1
      source.photonFlux       = float(source.photonFlux.split("<")[1].strip())
      source.photonFluxError  = -1
    pass
    fluxes[i]                 = source.flux
    fluxes_errors[i]          = source.fluxError
    phfluxes[i]               = source.photonFlux
    phfluxes_errors[i]        = source.photonFluxError
    TSs[i]                    = float(source.TS)
    phIndexes[i]              = float(source.photonIndex)
  pass
  
  if(totalCounts!=totalInputCounts):
    raise RuntimeError("We have losted somewhere %s counts!" %(totalInputCounts-totalCounts))
  pass
  
  #Now compute the SED points
  MeV2Erg                     = 1.60217657e-6
  ee1                         = numpy.array(energyBoundaries[:-1])
  ee2                         = numpy.array(energyBoundaries[1:])
  ee                          = (ee1+ee2)/2.0
  de                          = (ee2-ee1)
  #Use the photon index of the total fit to compute the mean energy
  pow                         = numpy.power
  meanEnergies                = numpy.array(map(lambda x:computeMeanEnergy(x[0],x[1],x[2]),zip(phIndexes,ee1,ee2)))
  nuFnu                       = phfluxes / de * pow(meanEnergies,2.0) * MeV2Erg
  nuFnuError                  = phfluxes_errors / de * pow(meanEnergies,2.0) * MeV2Erg

  
  #Print the results of the SED
  fw                           = open(sedtxt,'w+')
  fw.write("#Energy_min Energy_Max Flux Flux_error PhotonFlux PhotonFluxError TS nuFnu_energy nuFnu_energy_negerr nuFnu_energy_poserr nuFnu_value nuFnu_value_error\n")
  fw.write("#MeV MeV erg/cm2/s erg/cm2/s ph/cm2/s ph/cm2/s - MeV MeV MeV erg/cm2/s erg/cm2/s\n")
  fw.write("#Total exposure: %s s\n" %(totalExposure))
  for e1,e2,f,fe,ph,phe,ts,ne,nee1,nee2,nuF,nuFe in zip(energyBoundaries[:-1],energyBoundaries[1:],fluxes,fluxes_errors,phfluxes,phfluxes_errors,TSs,meanEnergies,meanEnergies-ee1,ee2-meanEnergies,nuFnu,nuFnuError):
    fw.write("%s %s %s %s %s %s %s %s %s %s %s %s\n" %(e1,e2,f,fe,ph,phe,ts,ne,nee1,nee2,nuF,nuFe))
    print("%10s - %10s MeV -> %g +/- %g erg/cm2/s, %g +/- %g ph/cm2/s, TS = %s" %(e1,e2,f,fe,ph,phe,ts))
  pass
  fw.close()
  
  if(figure!=None):  
    #Display the SED
    if(os.environ.get('DISPLAY')==None):
      os.environ.set('DISPLAY','/dev/null')
      import matplotlib
      matplotlib.use('Agg')
    pass
    
    import matplotlib.pyplot as plt
    try:
      figure.clear()
    except:
      print("Creating new figure...")
      try:
        figure                = plt.figure()  
      except:
        plt.switch_backend('Agg')
        figure                = plt.figure() 
    pass
    sub                       = figure.add_subplot(111)
    sub.errorbar(meanEnergies,nuFnu,xerr=[meanEnergies-ee1,ee2-meanEnergies],yerr=nuFnuError,fmt='.')
    sub.set_xlabel("Energy (MeV)")
    sub.set_ylabel("Flux (erg/cm2/s)")
    sub.loglog()
    sub.set_xlim(0.9*min(ee1),1.1*max(ee2))
    
    figure.canvas.draw()
    figure.savefig("%s.png" % ".".join(sedtxt.split(".")[0:-1]))
  pass
    
  return 'sedtxt', sedtxt
pass

def computeMeanEnergy(phIndex,e1,e2):
  return scipy.integrate.quad(lambda x:x**(phIndex+1),e1,e2)[0]/scipy.integrate.quad(lambda x:x**(phIndex),e1,e2)[0]

thisCommand.run = run

if __name__=='__main__':
  thisCommand.greetings()
  #Get all key=value pairs as a dictionary
  args                           = dict(arg.split('=') for arg in sys.argv[1:])
  gtdosed(**args)
pass
