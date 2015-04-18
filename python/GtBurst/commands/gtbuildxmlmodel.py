#!/usr/bin/env python

from GtBurst import dataHandling
from GtBurst import bkge
import sys, copy
import os, pyfits, numpy
from GtBurst import commandDefiner
from GtBurst import LikelihoodComponent
from GtBurst import dataHandling
from GtBurst.GtBurstException import GtBurstException

if(bkge.active):
  possibleParticleModels = ['isotr with pow spectrum', 'isotr template', 'none', 'bkge']
else:
  possibleParticleModels = ['isotr with pow spectrum', 'isotr template', 'none']
################ Command definition #############################
executableName                = "gtbuildxmlmodel"
version                       = "1.0.0"
shortDescription              = "Produce the XML model for the likelihood analysis."
author                        = "G.Vianello, giacomov@slac.stanford.edu"
thisCommand                   = commandDefiner.Command(executableName,shortDescription,version,author)

#Define the command parameters
thisCommand.addParameter("filteredeventfile","Input event list (FT1 file)",commandDefiner.MANDATORY,partype=commandDefiner.DATASETFILE,extension="fit")
thisCommand.addParameter("ra","R.A. of the point source (probably a GRB or the Sun)",commandDefiner.MANDATORY)
thisCommand.addParameter("dec","Dec of the point source (probably a GRB or the Sun)",commandDefiner.MANDATORY)
thisCommand.addParameter("triggername","Name of the source",commandDefiner.OPTIONAL,'GRB')
thisCommand.addParameter("particle_model",'''Model for the particle background (possible values: 
                                            'isotr with pow spectrum', 'isotr template', 'none')''',commandDefiner.MANDATORY,
                                         'isotr with pow spectrum',
                                         possiblevalues=possibleParticleModels)
thisCommand.addParameter("galactic_model",'''Model for the Galactic background (possible values:
                                             'template (fixed norm.)', 'template', 'none')''',commandDefiner.MANDATORY,
                                         'template (fixed norm.)',
                                         possiblevalues=['template (fixed norm.)','template','none'])
thisCommand.addParameter("source_model",'''Spectral model for the new source (GRB or SF).''',
                                           commandDefiner.MANDATORY,
                                         'PowerLaw2',
                                         possiblevalues=LikelihoodComponent.availableSourceSpectra.keys())

thisCommand.addParameter("ft2file","Spacecraft file (FT2)",commandDefiner.OPTIONAL,partype=commandDefiner.DATASETFILE,extension="fits")
thisCommand.addParameter("xmlmodel","Name for the output file for the XML model",commandDefiner.MANDATORY,partype=commandDefiner.OUTPUTFILE,extension="xml")
thisCommand.addParameter("clobber","Overwrite output file? (possible values: 'yes' or 'no')",commandDefiner.OPTIONAL,"yes")
thisCommand.addParameter("verbose","Verbose output (possible values: 'yes' or 'no')",commandDefiner.OPTIONAL,"yes")

GUIdescription                = "You have to choose which model include in the likelihood analysis."
GUIdescription               += " See http://fermi.gsfc.nasa.gov/ssc/data/analysis/scitools/source_models.html for the list"
GUIdescription               += " of available spectral model for the source_model parameter."
GUIdescription               += "TIP Use 'PowerLaw2' for normal GRB analysis. For TRANSIENT class data you should use "
GUIdescription               += "'isotr with pow spectrum' for the particle background and 'template (fixed norm.)' for "
GUIdescription               += "the Galactic component. For SOURCE class data you should use "
GUIdescription               += "'isotr template' for the particle background and 'template' for the Galactic component."
GUIdescription               += " The latter indeed include already the residual particle contamination in SOURCE data."

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

def gtbuildxmlmodel(**kwargs):
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
    ra                          = thisCommand.getParValue('ra')
    dec                         = thisCommand.getParValue('dec')
    particlemodel               = thisCommand.getParValue('particle_model')
    galacticmodel               = thisCommand.getParValue('galactic_model')
    sourcemodel                 = thisCommand.getParValue('source_model')
    filteredeventfile           = thisCommand.getParValue('filteredeventfile')
    xmlmodel                    = thisCommand.getParValue('xmlmodel')
    triggername                 = thisCommand.getParValue('triggername')
    ft2file                     = thisCommand.getParValue('ft2file')
    clobber                     = _yesOrNoToBool(thisCommand.getParValue('clobber'))
    verbose                     = _yesOrNoToBool(thisCommand.getParValue('verbose'))
  except KeyError as err:
    print("\n\nERROR: Parameter %s not found or incorrect! \n\n" %(err.args[0]))
    
    #Print help
    print thisCommand.getHelp()
    return
  pass
  
  #Get the IRF from the event file
  try:
    f                             = pyfits.open(filteredeventfile)
  except:
    raise GtBurstException(31,"Could not open filtered event file %s" %(filteredeventfile))
  
  tstart                        = float(f[0].header['_TMIN'])
  tstop                         = float(f[0].header['_TMAX'])
  irf                           = str(f[0].header['_IRF'])
  ra                            = float(f[0].header['_ROI_RA'])
  dec                           = float(f[0].header['_ROI_DEC'])
  roi                           = float(f[0].header['_ROI_RAD'])
  
  #Lookup table for the models
  models = {}
  if(particlemodel=='isotr with pow spectrum'):
    models['isotr with pow spectrum'] = LikelihoodComponent.IsotropicPowerlaw()
  elif(particlemodel=='isotr template'):
    models['isotr template']          = LikelihoodComponent.IsotropicTemplate(irf)
  pass
  
  if(galacticmodel=='template'):
    models['template']                = LikelihoodComponent.GalaxyAndExtragalacticDiffuse(irf,ra,dec,2.5*roi)
  elif(galacticmodel=='template (fixed norm.)'):
    models['template (fixed norm.)']  = LikelihoodComponent.GalaxyAndExtragalacticDiffuse(irf,ra,dec,2.5*roi)
    models['template (fixed norm.)'].fixNormalization()
  pass
  
  deltat                        = numpy.sum(f['GTI'].data.field('STOP')-f['GTI'].data.field('START'))
  f.close()
  triggertime                   = dataHandling.getTriggerTime(filteredeventfile)
  
  if(irf.lower().find('source')>=0 and particlemodel!='isotr template'):
    raise GtBurstException(6,"Do not use '%s' as model for the particle background in SOURCE class. Use '%s' instead." 
                     %(particlemodel,'isotropic template'))
  
  modelsToUse                   = [LikelihoodComponent.PointSource(ra,dec,triggername,sourcemodel)]
  if(particlemodel!='none'):
    if(particlemodel=='bkge'):
      if(ft2file==None or ft2file==''):
        raise ValueError("If you want to use the BKGE, you have to provide an FT2 file!")
      
      modelsToUse.append(LikelihoodComponent.BKGETemplate(filteredeventfile,
                                                          ft2file,tstart,tstop,triggername,triggertime))
    else:
      modelsToUse.append(models[particlemodel])
  if(galacticmodel!='none'):
    modelsToUse.append(models[galacticmodel])
  
  xml                          = LikelihoodComponent.LikelihoodModel()
  xml.addSources(*modelsToUse)
  xml.writeXML(xmlmodel)
  xml.add2FGLsources(ra,dec,float(roi)+8.0,xmlmodel,deltat)
    
  
  dataHandling._writeParamIntoXML(xmlmodel,IRF=irf,OBJECT=triggername,RA=ra,DEC=dec)
    
  return 'xmlmodel', xmlmodel
pass

thisCommand.run = run

if __name__=='__main__':
  thisCommand.greetings()
  #Get all key=value pairs as a dictionary
  args                           = dict(arg.split('=') for arg in sys.argv[1:])
  gtbuildxmlmodel(**args)
pass
