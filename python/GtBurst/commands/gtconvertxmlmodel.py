#! /usr/bin/env python

import sys
import os, pyfits, numpy, shutil
from GtBurst import commandDefiner
available                     = True
try:
  from uw.utilities.xml_parsers import parse_sources
  import uw.like.roi_monte_carlo
except:
  available                   = False
  
  
################ Command definition #############################
executableName                = "gtconvertxmlmodel"
version                       = "1.0.0"
shortDescription              = "Produce the XML model for gtobssim simulation."
author                        = "N.Omodei, nicola.omodei@stanford.edu"
thisCommand                   = commandDefiner.Command(executableName,shortDescription,version,author)

#Define the command parameters
thisCommand.addParameter("likexmlresults","Input XML file from a Likelihood fit",commandDefiner.MANDATORY,partype=commandDefiner.INPUTFILE,extension="xml")
thisCommand.addParameter("emin","Minimum Energy",commandDefiner.OPTIONAL,30.0)
thisCommand.addParameter("emax","Maximum Energy",commandDefiner.OPTIONAL,1.0e5)
thisCommand.addParameter("xmlsimmodel","Name for the output file for the XML model for the simulation",commandDefiner.MANDATORY,partype=commandDefiner.OUTPUTFILE,extension="xml")
thisCommand.addParameter("clobber","Overwrite output file? (possible values: 'yes' or 'no')",commandDefiner.OPTIONAL,"yes")
thisCommand.addParameter("verbose","Verbose output (possible values: 'yes' or 'no')",commandDefiner.OPTIONAL,"yes")

GUIdescription                = "In this step you have to convert the likelihood model from the gtlike format to the"
GUIdescription               += " gtobssim format."
GUIdescription               += "TIP If you don't know what I'm talking about, just click 'run'!"

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

def gtconvertxmlmodel(**kwargs):
  run(**kwargs)
pass

def run(**kwargs):
  if(not available):
      raise RuntimeError("The command gtconvertxmlmodel.py is not currently usable with public Science Tools")
  if(len(kwargs.keys())==0):
    #Nothing specified, the user needs just help!
    thisCommand.getHelp()
    return
  pass
  
  #Get parameters values
  thisCommand.setParValuesFromDictionary(kwargs)
  try:
    xmlmodel                    = thisCommand.getParValue('likexmlresults')
    Emin                        = float(thisCommand.getParValue('emin'))
    Emax                        = float(thisCommand.getParValue('emax'))
    xmlsimmodel                 = thisCommand.getParValue('xmlsimmodel')  
    clobber                     = _yesOrNoToBool(thisCommand.getParValue('clobber'))
    verbose                     = _yesOrNoToBool(thisCommand.getParValue('verbose'))
  except KeyError as err:
    print("\n\nERROR: Parameter %s not found or incorrect! \n\n" %(err.args[0]))    
    #Print help
    print thisCommand.getHelp()
    return
  
  from GtBurst import dataHandling
  irf                         = dataHandling._getParamFromXML(xmlmodel,'IRF')
  ra                          = dataHandling._getParamFromXML(xmlmodel,'RA')
  dec                         = dataHandling._getParamFromXML(xmlmodel,'DEC')
  name                        = dataHandling._getParamFromXML(xmlmodel,'OBJECT')
  
  if(irf==None):
    print("\n\nWARNING: could not read IRF from XML file. Be sure you know what you are doing...")
  
  sourceList                  = xmlmodel.replace('.xml','.txt')
  
  #Quick fix: MCModelBuilder cannot integrate a isotropic model if it has not a normalization of 1
  #We will edit the XML model, put temporarily the normalization of the IsotropicTemplate to 1,
  #convert the XML, then multiply the output normalization by the factor contained at the beginning
  tmpxml                      = "__temp__xmlmodel.xml"
  shutil.copy(xmlmodel,tmpxml)
  originalNorm                = dataHandling.getIsotropicTemplateNormalization(xmlmodel)
  if(originalNorm!=None or originalNorm!=1):
    dataHandling.setIsotropicTemplateNormalization(tmpxml,1)
  else:
    #Either the template is not in the XML file (possibly because the user used Transient class),
    #or it is already 1, nothing to do
    originalNorm              = 1
  pass
  
  ps,ds                       = parse_sources(tmpxml)
  sources                     = ps
  sources.extend(ds)
  
  mc                          = uw.like.roi_monte_carlo.MCModelBuilder(sources,savedir='.',emin=Emin,emax=Emax)
  mc.build(xmlsimmodel)
  
  dataHandling.multiplyIsotropicTemplateFluxSim(xmlsimmodel,originalNorm)
  
  os.remove(tmpxml)
  
  txt=''
  for x in sources:
    txt                      += x.name.replace('2FGL ','_2FGL_').replace('-','m').replace('.','')+'\n'
  
  file(sourceList,'w').writelines(txt)
  lines                       = file(xmlsimmodel,'r').readlines()
  newlines                    =''
  pwd                         = os.environ['PWD']
  for l in lines:
    newlines                 += l.replace('$($SIMDIR)',pwd)
  pass
  
  file(xmlsimmodel,'w').writelines(newlines)
  
  if(irf!=None):
    dataHandling._writeParamIntoXML(xmlsimmodel,IRF=irf,OBJECT=name,RA=ra,DEC=dec)
  pass    
  
  return 'xmlsimmodel', xmlsimmodel, 'srclist', sourceList
pass

thisCommand.run = run

if __name__=='__main__':
  thisCommand.greetings()
  #Get all key=value pairs as a dictionary
  args                           = dict(arg.split('=') for arg in sys.argv[1:])
  gtconvertxmlmodel(**args)
pass
