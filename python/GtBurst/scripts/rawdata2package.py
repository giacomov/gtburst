#!/usr/bin/env python

# Transform an FT1 and an FT2 downloaded from the Data server
# into a package for gtburst

from GtBurst.dataHandling import _makeDatasetsOutOfLATdata
import sys
import os, shutil

try:
    
    from astropy.io.fits import pyfits

except:
    
    import pyfits

if __name__=="__main__":
    
    if len(sys.argv) < 7:
        
        print("Usage: %s [ft1] [ft2] [triggertime] [triggername] [ra] [dec]" 
              % sys.argv[0])
        
        sys.exit(0)
    
    ft1 = sys.argv[1]
    ft2 = sys.argv[2]
    triggertime = float(sys.argv[3])
    triggername = sys.argv[4]
    ra = sys.argv[5]
    dec = sys.argv[6]
    
    # Rename ft1 and ft2
    new_ft1 = 'gll_ft1_tr_bn%s_v00.fit' % triggername
    new_ft2 = 'gll_ft2_tr_bn%s_v00.fit' % triggername
    
    shutil.copy(ft1, new_ft1)
    shutil.copy(ft2, new_ft2)
    
    # Get start and stop from ft1
    tstart = pyfits.getval(new_ft1,'TSTART','EVENTS')
    tstop = pyfits.getval(new_ft1,'TSTOP','EVENTS')
    
    _makeDatasetsOutOfLATdata(new_ft1,
                              new_ft2,
                              triggername,
                              tstart,
                              tstop,
                              ra,
                              dec,
                              triggertime,
                              '.',
                              triggertime,
                              triggertime+1000)
