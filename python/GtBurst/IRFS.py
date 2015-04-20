import collections
import os

class IRF(object):
  def __init__(self,shortname,name,reprocVer,evclass,galacticTemplate='',isotropicTemplate=''):
    self.shortname            = shortname
    self.name                 = name
    self.reprocessingVersion  = reprocVer
    self.evclass              = evclass
    self.galacticTemplate     = galacticTemplate
    self.isotropicTemplate    = isotropicTemplate
  pass
  
  def validateReprocessing(self,reproc):
    if(str(reproc) in self.reprocessingVersion.split(",")):
      return True
    else:
      return False
    pass
  pass
  
pass

class CaseInsensitiveDict(collections.OrderedDict):
  def __setitem__(self, key, value):
      super(CaseInsensitiveDict, self).__setitem__(key.lower(), value)
  pass
  
  def __getitem__(self, key):
      try:
        item                    = super(CaseInsensitiveDict, self).__getitem__(key.lower())
      except:
        #Try with the short name
        item                    = filter(lambda x:x.name==key,self.values())[0]
      pass
      return item
  pass
pass

def isOfClass(cl,evclass):
  bitmask                     = 1 << evclass
  if(cl & bitmask != 0):
    return True
  else:
    return False
  pass
pass


def fromEvclassToIRF(rep,event_class):
  try:
  
    _                         = (e for e in event_class)
  
  except TypeError:
  
    #event_class is not an iterable. We are dealing with data
    # <= P7REP
    
    #This assumes that classes are one into the other
    for i in range(1,6):
      
      if(i==1 and str(rep)=='202'):
        #In P7, evclass=1 is random (and must not be used, nor tested)
        continue
      pass
      
      if(isOfClass(event_class,i)==False):
        break
      pass
    pass
    
    evclass                     = i-1
    if(evclass==1 and str(rep)=='202'):
      evclass                   = 0
    pass
    
    #print("Evclass is %s for event_class %s" %(evclass,event_class))
  
  else:
    #event_class is an iterable (hopefully a bit mask),
    #so we are dealing with Pass 8 data (> v4 or above)
    
    #The left-ermost "on" bit of the first 10 bits in the bit mask (actually,
    #since bitmasks are numbered starting from the right, the last 10 bits)
    #corresponds to the most stringent selection which the event belongs to
    exponent                  = None
    for i in range(21,32):
      if(event_class[i]==True):
        exponent              = i
        break
      pass
    pass
    
    evclass                   = pow(2,32-exponent-1)
  pass
  
  irfsForThisRepr             = PROCS[rep]
  for irf in irfsForThisRepr:
    if(IRFS[irf].evclass==evclass):
      return irf
    pass
  pass
pass


IRFS                          = CaseInsensitiveDict()

#P7REP
IRFS['P7REP_TRANSIENT']   = IRF('P7REP_TRANSIENT','P7REP_TRANSIENT_V15','202,203',0,'gll_iem_v05_rev1.fit,gll_iem_v05_rev1.fits,gll_iem_v05.fits,gll_iem_v05.fit,template_4years_P7_v15_repro_v2_trim.fits','iso_transient_v05.txt')
IRFS['P7REP_SOURCE']      = IRF('P7REP_SOURCE','P7REP_SOURCE_V15','202,203',2,'gll_iem_v05_rev1.fit,gll_iem_v05_rev1.fits,gll_iem_v05.fits,gll_iem_v05.fit,template_4years_P7_v15_repro_v2_trim.fits','iso_source_v05_rev1.txt,iso_source_v05.txt')
IRFS['P7REP_CLEAN']       = IRF('P7REP_CLEAN','P7REP_CLEAN_V15','202,203',3,'gll_iem_v05_rev1.fit,gll_iem_v05_rev1.fits,gll_iem_v05.fits,gll_iem_v05.fit,template_4years_P7_v15_repro_v2_trim.fits','iso_clean_v05.txt')
IRFS['P7REP_ULTRACLEAN']  = IRF('P7REP_ULTRACLEAN','P7REP_ULTRACLEAN_V15','202,203',4,'gll_iem_v05_rev1.fit,gll_iem_v05_rev1.fits,gll_iem_v05.fits,gll_iem_v05.fit,template_4years_P7_v15_repro_v2_trim.fits','iso_clean_v05.txt')


#Pass 8 final (?)
galactic='template_4years_P8_V2_scaled.fits, gll_iem_v06.fits'

IRFS['P8_TRANSIENT100E']    = IRF('P8_TRANSIENT100E' ,'P8R2_TRANSIENT100E_V6' ,'302',     2, galactic, 'isotropic_transient_r020_4years_P8V4_rev3.txt, iso_P8R2_TRANSIENT020_V6_v06.txt') # YOU SHOULD USE THE BKGE FOR THIS 
IRFS['P8_TRANSIENT100']     = IRF('P8_TRANSIENT100' ,'P8R2_TRANSIENT100_V6'  ,'302',     4, galactic, 'isotropic_transient_r020_4years_P8V4_rev3.txt, iso_P8R2_TRANSIENT020_V6_v06.txt') # YOU SHOULD USE THE BKGE FOR THIS 
IRFS['P8_TRANSIENT020E']    = IRF('P8_TRANSIENT020E' ,'P8R2_TRANSIENT020E_V6' ,'302',     8, galactic, 'isotropic_transient_r020_4years_P8V4_rev3.txt, iso_P8R2_TRANSIENT020E_V6_v06.txt')
IRFS['P8_TRANSIENT020']     = IRF('P8_TRANSIENT020' ,'P8R2_TRANSIENT020_V6'  ,'302',    16, galactic, 'isotropic_transient_r020_4years_P8V4_rev3.txt, iso_P8R2_TRANSIENT020_V6_v06.txt')
IRFS['P8_TRANSIENT010E']    = IRF('P8_TRANSIENT010E' ,'P8R2_TRANSIENT010E_V6' ,'302',    32, galactic, 'isotropic_transient_r010_4years_P8V4_rev3.txt, iso_P8R2_TRANSIENT010E_V6_v06.txt')
IRFS['P8_TRANSIENT010']     = IRF('P8_TRANSIENT010' ,'P8R2_TRANSIENT010_V6'  ,'302',    64, galactic, 'isotropic_transient_r010_4years_P8V4_rev3.txt, iso_P8R2_TRANSIENT010E_V6_v06.txt')
IRFS['P8_SOURCE']           = IRF('P8_SOURCE'        ,'P8R2_SOURCE_V6'       ,'302',   128, galactic, 'isotropic_source_4years_P8V3.txt, iso_P8R2_SOURCE_V6_v06.txt')
IRFS['P8_CLEAN']            = IRF('P8_CLEAN'         ,'P8R2_CLEAN_V6'       ,'302',   256, galactic, 'isotropic_clean_4years_P8V3.txt, iso_P8R2_CLEAN_V6_v06.txt')
IRFS['P8_ULTRACLEAN']       = IRF('P8_ULTRACLEAN' ,'P8R2_ULTRACLEAN_V6'    ,'302',   512, galactic, 'isotropic_ultraclean_4years_P8V3.txt, iso_P8R2_ULTRACLEAN_V6_v06.txt')
IRFS['P8_ULTRACLEANVETO']   = IRF('P8_ULTRACLEANVETO','P8R2_ULTRACLEANVETO_V6','302',  1024, galactic, 'isotropic_ultraclean_4years_P8V3.txt, iso_P8R2_ULTRACLEANVETO_V6_v06.txt')
IRFS['P8_TRANSIENT100S']    = IRF('P8_TRANSIENT100S' ,'P8R2_TRANSIENT100S_V6' ,'302', 32768, galactic, 'isotropic_transient_r020_4years_P8V4_rev3.txt, iso_P8R2_TRANSIENT0100S_V6_v06.txt') # YOU SHOULD USE THE BKGE FOR THIS 
IRFS['P8_TRANSIENT015S']    = IRF('P8_TRANSIENT015S' ,'P8R2_TRANSIENT015S_V6' ,'302', 65536, galactic, 'isotropic_transient_r020_4years_P8V4_rev3.txt, iso_P8R2_TRANSIENT015S_V6_v06.txt')

PROCS                         = collections.OrderedDict()
for k,v in IRFS.iteritems():
  thisReprocessings       = v.reprocessingVersion.split(",")
  for repro in thisReprocessings:
    if(repro in PROCS.keys()):
      PROCS[repro].append(k)
    else:
      PROCS[repro] = [k]
    pass
  pass
pass
  
