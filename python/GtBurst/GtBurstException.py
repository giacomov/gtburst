
codes = {}
codes[1] = 'No network or generic network failure'
codes[11] = 'LAT server time out'
codes[12] = 'LAT data server is probably down'
codes[13] = 'Corrupted downloaded file'
codes[14] = 'No data coverage'
codes[2] = 'No events survived the data cuts'
codes[21] = 'Too few counts for the likelihood analysis'
codes[22] = "gtmktime failed"
codes[23] = "gtselect failed"
codes[24] = "gtbin failed during skymap production"
codes[25] = "gtbin failed during skycube production"
codes[26] = "gtltcube failed"
codes[27] = "gtexpmap failed"
codes[28] = "gtexpcube2 failed"
codes[29] = "gtsrcmaps failed"
codes[201] = "gtmodel failed"
codes[202] = "gtdiffrsp failed"
codes[203] = "gtrspgen failed"
codes[204] = "gtbin failed during PHA1 production"
codes[205] = "gtbkg failed"
codes[206] = "gttsmap failed"
codes[207] = "gtfindsrc failed"

codes[3] = "I/O error"
codes[31] = "Error opening filtered event file"
codes[4] = "Could not update"

codes[4] = "Spacecraft file (FT2 file) does not cover the interval requested"
codes[41] = "Spacecraft file (FT2 file) starts after the beginning of the requested interval"
codes[42] = "Spacecraft file (FT2 file) stops before the end of the requested interval"

codes[5] = "LLE or GBM data are not available"

codes[6] = "Wrong Isotropic component"

codes[60] = "No Isotropic template for selected class"
codes[61] = "No Galactic template for selected class"

codes[7] = "The provided irf is not supported by the Background Estimator"

class GtBurstException(RuntimeError):
  def __init__(self,code,message):
    RuntimeError.__init__(self,message)
    self.shortMessage         = codes[code]
    self.longMessage          = message
    self.code                 = code
  pass
###
