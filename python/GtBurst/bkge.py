import pyfits
import os

from GtBurst.GtBurstException import GtBurstException

try:
  import BKGE_interface
except:
  active                      = False
else:
  active                      = True
finally:
  pass

systematicError = 0.15 # 15%

class BKGE(object):
  def __init__(self,filteredFt1,ft2,triggerName,triggertime,outdir):
    global active
    if(active):
      self.ft1                = filteredFt1
      self.ft2                = ft2
      
      #Read the cuts from the filtered ft1 file
      f                       = pyfits.open(self.ft1)
      h                       = f[0].header
      self.ra                 = float(h['_ROI_RA'])
      self.dec                = float(h['_ROI_DEC'])
      self.roi                = float(h['_ROI_RAD'])
      self.emin               = float(h['_EMIN'])
      self.emax               = float(h['_EMAX'])
      self.zmax               = float(h['_ZMAX'])
      self.irf                = str(h['_IRF'])
      f.close()
      
      self.triggertime        = triggertime
      
      self.grbname            = triggerName
      self.outdir             = outdir
    else:
      raise RuntimeError("BKGE is not available in your system, you cannot use it!")
  pass
  
  def makeLikelihoodTemplate(self,start,stop,chatter=1):
    #Transform in relative time (the BKGE wants that!)
    start                     = float(start)-int(float(start) > 231292801.000)*self.triggertime
    stop                      = float(stop)-int(float(stop) > 231292801.000)*self.triggertime
    outdir                    = self.outdir+'/Bkg_Estimates/%.2f_%.2f/' %(start,stop)
    
    try:
      _                       = BKGE_interface.allowedIRFS
    except AttributeError:
      if(self.irf.upper().find("P8")>=0):
        raise RuntimeError("Looks like you are using the old Background Estimator,"+
                           " and Pass 8 IRFS. You cannot do that. You have to update"+
                           " your Science Tools.")
      else:
         #It is fine, this is the old BKGE with P7
         pass
      pass
    
    else:
      #Using the new version of the BKGE
      if(not self.irf.upper() in BKGE_interface.allowedIRFS):
         raise GtBurstException(7,"IRF %s is not supported by the BKGE" %(self.irf))
      
      else:
        BKGE_interface.setResponseFunction(self.irf.upper())
    
    try:
      BKGE_interface.MakeGtLikeTemplate(start, stop, self.triggertime, 
                                      self.ra, self.dec, 
                                      self.ft1, self.ft2, OUTPUT_DIR=self.outdir, 
                                      chatter=10, ROI_Radius=self.roi, 
                                      GRB_NAME=self.grbname)
    except:
      print("ERROR executing the BKGE")
    
    bkgetemplate              = os.path.abspath(os.path.join(outdir,'%s_gtlike_%s_CR_EGAL.txt' %(self.irf,self.grbname)))
    statisticalError          = 0
    
    return bkgetemplate, statisticalError, systematicError
  pass
pass
