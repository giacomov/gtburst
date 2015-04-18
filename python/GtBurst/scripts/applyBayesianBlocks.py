#!/usr/bin/env python
import argparse

import os
import logging
import numpy

from GtBurst import BayesianBlocks

try:
  import astropy.io.fits as pyfits
except:
  import pyfits

parser                        = argparse.ArgumentParser("Apply the Bayesian Blocks algorithm on the input data")

parser.add_argument("--infile", 
                     help="FT1 or TTE data",
                     type=str,required=True)

parser.add_argument("--probability",
                     help="Null-hypothesis probability for the BB algorithm",
                     type=float,required=True)

parser.add_argument("--outfile", 
                     help="File for the results (will be overwritten)",
                     type=str,required=True)

#Main code
if __name__=="__main__":
  args                        = parser.parse_args()
  
  if( not os.path.exists(args.infile)):
    raise RuntimeError("File %s does not exist" %(args.infile))
    
  #Read input file
  with pyfits.open(args.infile) as f:
    
    data = f['EVENTS'].data
    
    tstart = f['EVENTS'].header.get("TSTART")
    tstop = f['EVENTS'].header.get("TSTOP")
    
    time = data.field("TIME")
    
    #This is probably useless, but sometimes input files
    #are not time ordered and the BB algorithm would 
    #crash
    
    time.sort()
    
    BayesianBlocks.logger.setLevel(logging.DEBUG)
    
    bb = BayesianBlocks.bayesian_blocks(time, tstart, tstop,
                                        args.probability)
    
    #Make the light curve
    
    counts = numpy.zeros(bb.shape[0]-1)
    
    _time = time[ time > bb[0]]
    
    for i,(t1,t2) in enumerate(zip(bb[:-1],bb[1:])):
      
      idx = (_time > t1) & (_time <= t2)
      counts[i] = numpy.sum(idx)
      _time = _time[~idx]
    
    with open(args.outfile,"w+") as f:
      
      f.write("#Tstart Tstop counts\n")
      
      for t1,t2,c in zip(bb[:-1],bb[1:],counts):
        
        f.write("%s %s %s\n" %(t1,t2,c))
