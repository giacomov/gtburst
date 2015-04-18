#! /usr/bin/env python

import sys
import os
from GtBurst import commandDefiner
import pyfits, numpy,math
import re

################ Command definition #############################
executableName                = "gtdotsmap"
version                       = "1.0.0"
shortDescription              = "Produce a TS map"
author                        = "G.Vianello, giacomov@slac.stanford.edu"
thisCommand                   = commandDefiner.Command(executableName,shortDescription,version,author)

#Define the command parameters
thisCommand.addParameter("filteredeventfile","Input event list (FT1 file)",commandDefiner.MANDATORY,partype=commandDefiner.DATASETFILE,extension="fit")
thisCommand.addParameter("rspfile","LAT response (RSP file)",commandDefiner.MANDATORY,partype=commandDefiner.DATASETFILE,extension="rsp")
thisCommand.addParameter("ft2file","Spacecraft file (FT2)",commandDefiner.MANDATORY,partype=commandDefiner.DATASETFILE,extension="fits")
thisCommand.addParameter("tsltcube","Pre-computed livetime cube",commandDefiner.OPTIONAL,partype=commandDefiner.DATASETFILE,extension="fits")
thisCommand.addParameter("tsexpomap","Pre-computed exposure map",commandDefiner.OPTIONAL,partype=commandDefiner.DATASETFILE,extension="fits")
thisCommand.addParameter("xmlmodel","XML model",commandDefiner.MANDATORY,partype=commandDefiner.DATASETFILE,extension="fits")
thisCommand.addParameter("tsmap","Name for the output file for the TS map",commandDefiner.MANDATORY,partype=commandDefiner.OUTPUTFILE,extension="fits")
#thisCommand.addParameter("skymap","Name for the for the sky map (needed only if you want to plot your results)",commandDefiner.OPTIONAL,partype=commandDefiner.INPUTFILE,extension="fit")
#thisCommand.addParameter("tsmin","Minimum TS to consider a source detected",commandDefiner.OPTIONAL,20)
#thisCommand.addParameter("optimizeposition","Optimize position?",commandDefiner.OPTIONAL,"yes",possiblevalues=['yes','no'])
#thisCommand.addParameter("showmodelimage","Show an image representing the best fit likelihood model?",commandDefiner.OPTIONAL,"yes",possiblevalues=['yes','no'])
thisCommand.addParameter("step","Size of the grid step (deg)",commandDefiner.OPTIONAL,0.8)
thisCommand.addParameter("side","Size of the side of the TS map (deg). NB: (side/step)^2 likelihood analysis will be run",commandDefiner.OPTIONAL,'auto')
thisCommand.addParameter("clobber","Overwrite output file? (possible values: 'yes' or 'no')",commandDefiner.OPTIONAL,"yes")
thisCommand.addParameter("verbose","Verbose output (possible values: 'yes' or 'no')",commandDefiner.OPTIONAL,"yes")
thisCommand.addParameter("figure","Matplotlib figure for the interactive mode",commandDefiner.OPTIONAL,None,partype=commandDefiner.PYTHONONLY)

GUIdescription                = "Here you will build a TS map of the ROI you defined in the first step,"
GUIdescription               += " using the model you selected in the 2nd step. A likelihood is performed in each"
GUIdescription               += " point of a grid of coordinates, then the data are tested for a source at that"
GUIdescription               += " coordinates. The TS is the difference in log Likelihood between the model without"
GUIdescription               += " the source and the model with the source."
GUIdescription               += "TIP The TS map should take between 5 and 10 minutes to complete."
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

def gtdotsmap(**kwargs):
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
    xmlmodel                    = thisCommand.getParValue('xmlmodel')
    tsltcube                    = thisCommand.getParValue('tsltcube')
    tsexpomap                   = thisCommand.getParValue('tsexpomap')
    tsmap                       = thisCommand.getParValue('tsmap')
    step                        = float(thisCommand.getParValue('step'))
    side                        = thisCommand.getParValue('side')
    if(side=='auto'):
      side                      = None
#    showmodelimage              = thisCommand.getParValue('showmodelimage')
#    optimize                    = thisCommand.getParValue('optimizeposition')
#    tsmin                       = float(thisCommand.getParValue('tsmin'))
#    skymap                      = thisCommand.getParValue('skymap')
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
  
  origra                      = float(dataHandling._getParamFromXML(xmlmodel,'RA'))
  origdec                     = float(dataHandling._getParamFromXML(xmlmodel,'DEC'))
  sourceName                  = dataHandling._getParamFromXML(xmlmodel,'OBJECT')
  
  #Verify that TS map, if provided, is compatible with the position in the XML
  if(tsexpomap!=None and tsexpomap!=''):
    if(os.path.exists(tsexpomap)):
      header                  = pyfits.getheader(tsexpomap)
      ra,dec                  = (float(header.get('CRVAL1')),float(header.get('CRVAL2')))
      angdist                 = getAngularDistance(origra,origdec,ra,dec)
      if(angdist > 0.1):
        print("Provided exposure map has a different center. Will compute it again.")
        tsexpomap             = None
    else:
      print("Provided exposure map does not exist. Will compute it again.")
      tsexpomap               = None
  
  LATdata                     = dataHandling.LATData(eventfile,rspfile,ft2file)
  tsmap                       = LATdata.makeTSmap(xmlmodel,sourceName,step,side,tsmap,tsltcube,tsexpomap)
  tsltcube                    = LATdata.livetimeCube
  tsexpomap                   = LATdata.exposureMap
  
  ra,dec,tsmax                = dataHandling.findMaximumTSmap(tsmap,tsexpomap)
  
  print("\nCoordinates of the maximum of the TS map in the allowed region (TS = %.1f):" %(tsmax))
  print("(R.A., Dec.)              = (%6.3f, %6.3f)\n" %(ra,dec))
  print("Distance from ROI center  = %6.3f\n\n" %(getAngularDistance(origra,origdec,ra,dec)))

  if(figure!=None):
    from GtBurst import aplpy   
    #Display the TS map    
    figure.clear()
    tsfig                       = aplpy.FITSFigure(tsmap,convention='calabretta',figure=figure)
    tsfig.set_tick_labels_font(size='small')
    tsfig.set_axis_labels_font(size='small')
    tsfig.show_colorscale(cmap='gist_heat',aspect='auto')
    tsfig.show_markers([ra], [dec], edgecolor='green', facecolor='none', marker='o', s=10, alpha=0.5)
    # Modify the tick labels for precision and format
    tsfig.tick_labels.set_xformat('ddd.dd')
    tsfig.tick_labels.set_yformat('ddd.dd')
    
    # Display a grid and tweak the properties
    tsfig.show_grid()
    
    figure.canvas.draw()
  pass
  
  return 'tsmap', tsmap, 'tsmap_ra', ra, 'tsmap_dec', dec, 'tsmap_maxTS', tsmax, 'tsltcube', tsltcube, 'tsexpomap', tsexpomap
pass

thisCommand.run = run

if __name__=='__main__':
  thisCommand.greetings()
  #Get all key=value pairs as a dictionary
  args                           = dict(arg.split('=') for arg in sys.argv[1:])
  gtdotsmap(**args)
pass
