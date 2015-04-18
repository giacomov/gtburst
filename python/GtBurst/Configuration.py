import os, errno
from GtBurst import commandDefiner
import shelve
packageName                   = 'pyBurstAnalysisGUI'
configDirEnvVariable          = 'GTBURSTCONFDIR'

class Configuration(object):
    def __init__(self):
      #The configuration file will be in the home directory of the user
      #This can be overridden by setting the environment variable GTBURSTCONFDIR
      configurationFileName             = "gtburstGUI.conf"
      
      if(os.environ.get(configDirEnvVariable)):
        targetDir                       = os.environ[configDirEnvVariable]
      else:
        targetDir                       = os.path.join(os.path.expanduser("~"),'.gtburst')
      pass
      
      #Create the directory if does not exist already
      try:
        os.makedirs(targetDir)
      except OSError as exception:
        if exception.errno==errno.EEXIST:
          #The file exists, fail if it is NOT a directory
          if not os.path.isdir(targetDir):
            raise IOError("Fatal error: %s exists but it is NOT a directory! Please remove that file and retry." %(targetDir))
          pass
        else:
          #Uncaught exception
          raise
        pass
      pass  
      
      #Now test that we can actually write there
      try:
        testFile                        = os.path.join(targetDir,'__pyBurstWriteTest')
        f                               = open(testFile,'w+')
        f.write("TEST\n")
        f.close()
        os.remove(testFile)
      except:
        print("WARNING: it seems that directory %s is not writeable by you. Fix this or use the environment variable %s to point to a writeable directory" %(targetDir,configDirEnvVariable))
      pass
      
      self.configurationFile            = os.path.join(targetDir,configurationFileName)
      
      #Try to load the configuration file. If this is the first time, an exception will be caught and a new
      #configuration with default values will be created
      try:
        #Load the configuration
        self.configuration              = shelve.open(self.configurationFile,writeback=True)
        self.dataRepository             = self.configuration['dataRepository']
        self.ftpWebsite                 = self.configuration['ftpWebsite']
        self.maxNumberOfCPUs            = self.configuration['maxNumberOfCPUs']
      except:
        #First time, or file corrupted. Create a configuration file with default values
        self.configuration              = shelve.open(self.configurationFile,writeback=True)
        self.configuration['dataRepository'] = os.path.join(os.path.expanduser('~'),'FermiData')
        self.configuration['ftpWebsite']    = "ftp://legacy.gsfc.nasa.gov/fermi/data"
        self.configuration['maxNumberOfCPUs'] = 15
        self.save()
        self.dataRepository             = self.configuration['dataRepository']
        self.ftpWebsite                 = self.configuration['ftpWebsite']
        self.maxNumberOfCPUs            = self.configuration['maxNumberOfCPUs']
      pass
      
      
      if(os.path.exists(self.dataRepository)):
        pass
      else:  
        #Create it!
        os.makedirs(os.path.abspath(self.dataRepository))
      pass
      
      self.description = {}
      self.description['dataRepository'] = 'Directory for the storage of data'
      self.description['ftpWebsite']     = 'FTP data repository'
      self.description['maxNumberOfCPUs']= 'Max. number of CPUs to use'
    pass
    
    def set(self,key,value):
      if(key in self.description.keys()):
        self.configuration[key] = value
        self.save()
      else:
        raise RuntimeError("Got a unknown key!")
    pass
    
    def get(self,key):
      if(key in self.description.keys()):
        return self.configuration[key]
      else:
        raise RuntimeError("Got a unknown key!")
    pass
    
    def getDescription(self,key):
      if(key in self.description.keys()):
        return self.description[key]
      pass
    pass
      
    def keys(self):
      return self.configuration.keys()
    pass
    
    def save(self):
      self.configuration.sync()
    pass
    
    def __del__(self):
      try:
        self.configuration.close()
      except:
        pass
    pass  
pass
