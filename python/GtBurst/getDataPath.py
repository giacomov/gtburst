import GtBurst
import os

def getDataPath():
  path                 = GtBurst.__file__
  installationPath     = os.path.join(os.path.sep.join(path.split(os.path.sep)[0:-3]))
  
  #Stand-alone version: data are in the 'data' subdir under the installationPath
  dataPath             = os.path.join(installationPath,'data')
  
  if(not os.path.exists(os.path.join(dataPath,'glast_logo.png'))):
    #In the SCONS version of Science Tools, data are saved in data/pyBurstAnalysisGUI/
    dataPath           = os.path.join(installationPath,'data','pyBurstAnalysisGUI')
    if(not os.path.exists(os.path.join(dataPath,'glast_logo.png'))):
      #In the public version of Fermi ST, data are in refdata/fermi/pyBurstAnalysisGUI
      installationPath = os.path.join(os.path.sep.join(path.split(os.path.sep)[0:-4]))
      dataPath         = os.path.join(installationPath,'refdata','fermi','pyBurstAnalysisGUI')
    pass
  pass
  
  #Final check
  if(not os.path.exists(os.path.join(dataPath,'glast_logo.png'))):
    raise RuntimeError("Fatal error: could not locate the data subdirectory.")
  pass
  
  return dataPath
