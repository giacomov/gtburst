#!/usr/bin/env python

import UnbinnedAnalysis

import argparse
from GtBurst import IRFS
from GtBurst.Configuration import Configuration
from GtBurst.commands import gtdocountsmap
from GtBurst.commands import gtbuildxmlmodel
from GtBurst.commands import gtdolike
from GtBurst import dataHandling
from GtBurst.fast_ts_map import FastTSMap
import os, subprocess, glob, shutil
import numpy,pyfits
import collections

import xml.etree.ElementTree as ET


def printCommand(cmdname,targs):
  commandLine = cmdname
  
  for k,v in targs.iteritems():
    commandLine += " %s='%s'" %(k,v)
  pass
  
  print("-> %s" %commandLine)
pass

def writeSourceListToFile(sources,outfile):
  colNames                       = ['name','ra','dec','tstart','tstop','TS','photonIndex','photonIndexError',
                                    'flux','fluxError','photonFlux','photonFluxError','roi','irf','zmax','thetamax','strategy']
    
  with open(outfile,'w+') as f:
    f.write("#%s" %(" ".join(colNames)))
    f.write("\n")
    for src in sources:
      vals                    = []
      for name in colNames:
        vals.append(str(src.__getattribute__(name)).replace(' ',''))
      pass
      f.write(" ".join(vals))
      f.write("\n")
    pass
  pass
pass


configuration                 = Configuration()
irfs                          = IRFS.IRFS.keys()
irfs.append('auto')
parser                        = argparse.ArgumentParser()

parser.add_argument("triggername",help="Trigger name (in Fermi format: YYMMDDXXX)",type=str)
parser.add_argument("--outfile",help="File for the results (will be overwritten)",type=str,required=True)
parser.add_argument("--ra",help="R.A. of the object (J2000)",type=float)
parser.add_argument("--dec",help="Dec. of the object (J2000)",type=float)
parser.add_argument("--roi",help="Radius of the Region Of Interest (ROI)",type=float,required=True)
parser.add_argument("--tstarts",help="Comma-separated list of start times (with respect to trigger)",type=str,required=True)
parser.add_argument("--tstops",help="Comma-separated list of stop times (with respect to trigger)",type=str,required=True)
parser.add_argument("--zmax",help="Zenith cut",type=float,default=100.0)
parser.add_argument("--emin",help="Minimum energy for the analysis",type=float,default=100.0)
parser.add_argument("--emax",help="Maximum energy for the analysis",type=float,default=100000.0)
parser.add_argument("--irf",help="Instrument Function to be used (IRF)",type=str,choices=irfs,required=True)
parser.add_argument("--galactic_model",help="Galactic model for the likelihood",type=str,required=True,choices=['template (fixed norm.)', 'template','none'])
parser.add_argument("--particle_model",help="Particle model",type=str,required=True,choices=['auto','isotr with pow spectrum', 'isotr template','none','bkge'])
parser.add_argument("--tsmin",help="Minimum TS to consider a detection",type=float,default=20)
parser.add_argument("--strategy",help="Strategy for Zenith cut: events or time",type=str,choices=['time','events'],default='time')
parser.add_argument("--thetamax",help="Theta cut",type=float,default=180)
parser.add_argument("--spectralfiles",help="Produce spectral files to be used in XSPEC?",type=str,choices=['yes','no'],default='no')
parser.add_argument("--liketype",help="Likelihood type (binned or unbinned)",type=str,default="unbinned",choices=['binned','unbinned'])
parser.add_argument("--optimizeposition",help="Optimize position with gtfindsrc?",type=str,default="no",choices=['yes','no'])
parser.add_argument("--datarepository",help="Directory where data are stored",default=configuration.get('dataRepository'))
parser.add_argument("--ltcube",help="Pre-computed livetime cube",default='',type=str)
parser.add_argument("--expomap",help="pre-computed exposure map",default='', type=str)
parser.add_argument('--ulphindex',help="Photon index for upper limits",default=-2,type=float)
parser.add_argument('--flemin',help="Lower bound energy for flux/upper limit computation",default=None)
parser.add_argument('--flemax',help="Upper bound energy for flux/upper limit computation",default=None)
parser.add_argument('--fgl_mode',help="Set 'complete' to use all FGL sources, set 'fast' to use only bright sources",default='fast')
parser.add_argument("--tsmap_spec", help="A TS map specification of the type half_size,n_side. For example: '--tsmap_spec 0.5,8' makes a TS map 1 deg x 1 deg with 64 points", default=None)

#Main code
if __name__=="__main__":
  args                        = parser.parse_args()
  
  if args.ltcube!='':
      
      args.ltcube = os.path.abspath(os.path.expanduser(os.path.expandvars(args.ltcube)))
  
  if args.expomap!='':
      
      args.expomap = os.path.abspath(os.path.expanduser(os.path.expandvars(args.expomap)))
  
  #Determine time intervals
  tstarts                     = numpy.array(map(lambda x:float(x.replace('\\',"")),args.tstarts.split(",")))
  tstops                      = numpy.array(map(lambda x:float(x.replace('\\',"")),args.tstops.split(",")))
  print("\nMaking likelihood analysis on the following intervals:")
  print("------------------------------------------------------")
  for t1,t2 in zip(tstarts,tstops):
    print("%-20s - %s" %(t1,t2))
  pass
  
  #Check if data exists, otherwise download them
  try:
    dataset                     = dataHandling.getLATdataFromDirectory(os.path.join(args.datarepository,'bn%s' %args.triggername.replace('bn','')))
  except:
    raise
  
  if(dataset==None):
    #Download data
    print("\nData for trigger %s are not available. Let's download them!" %(args.triggername))
    cmdLine                   = "gtdownloadLATdata.py triggername=%s timebefore=%s timeafter=%s datarepository=%s" %(args.triggername,
                                                                                                   min(tstarts.min(),-5000),
                                                                                                   max(tstarts.max(),10000),
                                                                                                   args.datarepository)
    subprocess.call(cmdLine,shell=True)
    dataset                   = dataHandling.getLATdataFromDirectory(os.path.join(args.datarepository,'bn%s' %args.triggername.replace('bn','')))
  pass
    
  print("\nData files:")
  print("-----------")
  for k,v in dataset.iteritems():
    print("%-20s %s" %(k,v))
  pass
  
  #Now get R.A. and Dec. if not specified
  if(args.ra==None or args.dec==None):
    header                      = pyfits.getheader(dataset['eventfile'],'EVENTS')
    ra,dec                      = (header['RA_OBJ'],header['DEC_OBJ'])
    args.ra                     = ra
    args.dec                    = dec
  else:
    ra                          = args.ra
    dec                         = args.dec
  pass
  
  print("\nROI:")
  print("-----")
  print("%-20s %s" %('R.A.',ra))
  print("%-20s %s" %('Dec.',dec))
  print("%-20s %s" %('Radius',args.roi))
  
  results                        = []
  initialWorkdir                 = os.getcwd()
  
  for i,t1,t2 in zip(range(1,len(tstarts)+1),tstarts,tstops):
    print("\nInterval # %s (%s-%s):" %(i,t1,t2))
    print("-----------------------\n")
    if(args.irf.lower().find('auto')>=0):
      if(t2-t1 <= 100.0):
        irf                      = 'p7rep_transient'
        particle_model           = 'bkge'        
      else:
        irf                      = 'p7rep_source'
        particle_model           = 'isotr template'
      pass
    else:
      particle_model             = args.particle_model
      irf                        = args.irf
    pass
    
    #Create a work dir and move there
    dirname                      = os.path.abspath("interval%s-%s" %(t1,t2))
    
    try:
      os.makedirs(dirname)
    except:
      pass
    pass
    
    try:
      os.chdir(dirname)
    except:
      raise RuntimeError("Could not create/access directory %s" %(dirname))
    pass
    
    #Select data
    targs                        = {}
    targs['rad']                 = args.roi
    targs['eventfile']           = dataset['eventfile']
    targs['zmax']                = args.zmax
    targs['thetamax']            = args.thetamax
    targs['emin']                = args.emin
    targs['emax']                = args.emax
    targs['skymap']              = '%s_LAT_skymap_%s-%s.fit' %(args.triggername,t1,t2)
    targs['rspfile']             = dataset['rspfile']
    targs['strategy']            = args.strategy
    targs['ft2file']             = dataset['ft2file']
    targs['tstart']              = t1
    targs['tstop']               = t2
    targs['ra']                  = args.ra
    targs['dec']                 = args.dec
    targs['irf']                 = irf
    targs['allowEmpty']          = 'no'
    
    printCommand("gtdocountsmap.py",targs)
    try:
      _, skymap, _, filteredeventfile, _, _, _, _ = gtdocountsmap.run(**targs)
    except:
      print("\nERROR: could not complete selection of data for this interval.")
      continue
    
    #Build XML file
    targs                        = {}
    targs['xmlmodel']            = '%s_LAT_xmlmodel_%s-%s.xml' %(args.triggername,t1,t2)
    targs['filteredeventfile']   = filteredeventfile
    targs['galactic_model']      = args.galactic_model
    targs['particle_model']      = particle_model
    targs['ra']                  = args.ra
    targs['dec']                 = args.dec
    targs['fgl_mode']            = args.fgl_mode
    targs['ft2file']             = dataset['ft2file']
    targs['source_model']        = 'powerlaw2'
    printCommand("gtbuildxmlmodel",targs)
    _,xmlmodel                   = gtbuildxmlmodel.run(**targs)
    
    # Now if the user has specified a specific photon index for upper limits,
    # change the photon index in the XML file
    
    # Save parameters in comments (ET will strip them out)
    
    pars_in_comments = {}
    
    for key in ['OBJECT','RA','DEC','IRF']:
        
        pars_in_comments[key] = dataHandling._getParamFromXML(xmlmodel,key)
    
    # Now change the photon index in the XML file
        
    tree = ET.parse(xmlmodel)
    root = tree.getroot()
    index = root.findall("./source[@name='%s']/spectrum/parameter[@name='Index']" % 'GRB')[0]
    
    if args.ulphindex==-1.0:
        
        args.ulphindex += 0.01
    
    index.set('value', str(args.ulphindex))
    
    tree.write(xmlmodel)
    
    # Add the parameters in comments back
    
    dataHandling._writeParamIntoXML(xmlmodel,**pars_in_comments)
    
    targs                        = {}
    targs['spectralfiles']       = args.spectralfiles
    targs['xmlmodel']            = xmlmodel
    targs['liketype']            = args.liketype
    targs['filteredeventfile']   = filteredeventfile
    targs['rspfile']             = dataset['rspfile']
    targs['showmodelimage']      = 'no'
    targs['tsmin']               = args.tsmin
    targs['optimizeposition']    = 'no'
    targs['ft2file']             = dataset['ft2file']
    targs['skymap']              = skymap
    targs['flemin']              = args.flemin
    targs['flemax']              = args.flemax
    
    if args.ltcube!='':
            
      if not os.path.exists(args.ltcube):
           
           raise IOError("Livetime cube %s does not exists!" %(args.ltcube))
      
      targs['ltcube']              = args.ltcube
      
    if args.expomap!='':
            
      if not os.path.exists(args.expomap):
           
           raise IOError("Exposure map %s does not exists!" %(args.expomap))
      
      targs['expomap']              = args.expomap
    
    printCommand("gtdolike.py",targs)
    (_, outfilelike, _, grb_TS, 
     _, bestra, _, bestdec, 
     _, poserr, _, distance, 
     _, sources)                 = gtdolike.run(**targs)
    
    # If the TS map is required, let's do it
    
    if args.tsmap_spec is not None:
        
        half_size,n_side = args.tsmap_spec.replace(" ","").split(",")
        
        # Get root of the name
        root_name = os.path.splitext(os.path.basename(filteredeventfile))[0]
        
        # Find ltcube
        
        ltcubes = glob.glob("%s_ltcube.fit*" % root_name)
        
        assert len(ltcubes) == 1, "Couldn't find ltcube"
        
        ltcube = ltcubes[0]
        
        # Find expomap
        
        expmaps = glob.glob("%s_expomap.fit*" % root_name)
        
        assert len(expmaps) == 1, "Couldn't find exopmap"
        
        expmap = expmaps[0]
        
        # Find XML model output of gtdolike
        xmls = glob.glob("%s_likeRes.xml" % root_name)
        
        assert len(xmls) == 1, "Couldn't find XML"
        
        xml_res = xmls[0]
        
        obs = UnbinnedAnalysis.UnbinnedObs(filteredeventfile, dataset['ft2file'], expMap=expmap, expCube=ltcube)
        like = UnbinnedAnalysis.UnbinnedAnalysis(obs, xml_res, 'MINUIT')
        
        ftm = FastTSMap(like)
        (bestra, bestdec), maxTS = ftm.search_for_maximum(args.ra, args.dec, float(half_size), int(n_side), verbose=False)
        
    
    #Now append the results for this interval
    grb                          = filter(lambda x:x.name.find("GRB")>=0,sources)[0]
    
    if args.tsmap_spec is not None:
        
        if maxTS > grb.TS:
            
            print("\n\n=========================================")
            print(" Fast TS Map has found a better position")
            print("=========================================\n\n")
            
            #grb.ra                   = float(bestra)
            #grb.dec                  = float(bestdec)
            grb.TS                   = float(maxTS)
            
            print("(R.A., Dec.) = (%.3f, %3f) with TS = %.2f\n" % (grb.ra, grb.dec, grb.TS))
                 
    else:
        
        # Do nothing, so that grb.ra and grb.dec will stay what they are already
        pass
    
    grb.name                     = args.triggername
    grb.tstart                   = t1
    grb.tstop                    = t2
    grb.roi                      = args.roi
    grb.irf                      = irf
    grb.zmax                     = args.zmax
    grb.thetamax                 = args.thetamax
    grb.strategy                 = args.strategy
    results.append(grb)
    
    os.chdir(initialWorkdir)
  pass
  
  try:
  
      writeSourceListToFile(results,args.outfile)
  
  except IOError:
      
      print("Looks like the analysis has failed. No output file produced!")
pass

