#! /usr/bin/env python

import sys
import os, pyfits, numpy
from GtBurst import commandDefiner
from GtBurst import xmlModelGUI

################ Command definition #############################
executableName                = "gteditxmlmodelsim"
version                       = "1.0.0"
shortDescription              = "Edit using a GUI the XML model for gtlike"
author                        = "G.Vianello, giacomov@slac.stanford.edu"
thisCommand                   = commandDefiner.Command(executableName,shortDescription,version,author)

#Define the command parameters
thisCommand.addParameter("likexmlresults","XML model file to edit",commandDefiner.MANDATORY,partype=commandDefiner.GENERICFILE,extension="xml")
thisCommand.addParameter("tkwindow","Tk root window",commandDefiner.OPTIONAL,None,partype=commandDefiner.PYTHONONLY)

GUIdescription                = "After clicking 'run', you can modify the parameters of your likelihood model"
GUIdescription               += "by double clicking on the parameter of interest and setting its new values."
GUIdescription               += "When you are done, click on 'Save' and then on 'done'."
GUIdescription               += "TIP Check and fix components with very small normalization"
GUIdescription               += " otherwise the simulation might fail."

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

def gteditxmlmodelsim(**kwargs):
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
    xmlmodel                    = thisCommand.getParValue('likexmlresults')
    tkwindow                    = thisCommand.getParValue('tkwindow')
  except KeyError as err:
    print("\n\nERROR: Parameter %s not found or incorrect! \n\n" %(err.args[0]))
    
    #Print help
    print thisCommand.getHelp()
    return
  pass
  
  from GtBurst import dataHandling
  irf                         = dataHandling._getParamFromXML(xmlmodel,'IRF')
  ra                          = dataHandling._getParamFromXML(xmlmodel,'RA')
  dec                         = dataHandling._getParamFromXML(xmlmodel,'DEC')
  name                        = dataHandling._getParamFromXML(xmlmodel,'OBJECT')
  
  xml                         = xmlModelGUI.xmlModelGUI(xmlmodel,tkwindow)
  
  if(irf!=None):
    dataHandling._writeParamIntoXML(xmlmodel,IRF=irf,OBJECT=name,RA=ra,DEC=dec)
  pass
    
  return 'likexmlresults', xmlmodel
pass

thisCommand.run = run

if __name__=='__main__':
  thisCommand.greetings()
  #Get all key=value pairs as a dictionary
  args                           = dict(arg.split('=') for arg in sys.argv[1:])
  gteditxmlmodelsim(**args)
pass
