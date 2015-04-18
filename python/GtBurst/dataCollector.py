#This is a mother class to get GBM and LLE data files (lle, pha and rsp)
#Author: giacomov@slac.stanford.edu

import os,sys,glob,pyfits,string,errno,shutil
from GtBurst.GtBurstException import GtBurstException
import ftplib, socket
import time
try:
  from Tkinter import *
except:
  #Silently accept when tkinter import fail (no X server?)
  pass
from GtBurst import downloadCallback
try:
  from GtBurst.lleProgressBar import Meter
except:
  #Silently accept when tkinter import fail (no X server?)
  pass

class dataCollector(object):
  def __init__(self,instrument,grbName,dataRepository=None,localRepository=None,
                    getTTE=True,getCSPEC=True,getRSP=True,getCTIME=True,**kwargs):
    
    self.parent               = None
    for key in kwargs.keys():
      if key.lower()=='parent' :  self.parent    = kwargs['parent']
    
    self.instrument           = instrument
    
    if(grbName.find("bn")==0):
      self.grbName            = grbName[2:]
    else:
      self.grbName            = grbName  
    pass
    
    self.trigName             = "bn%s" %(self.grbName)
    
    self.dataRepository       = dataRepository
        
    self.localRepository      = os.path.join(localRepository,self.trigName)
        
    self.getCTIME              = getCTIME
    self.getCSPEC              = getCSPEC
    self.getTTE                = getTTE
    self.getRSP                = getRSP    
  pass
  
  def makeLocalDir(self):
    try:
      os.makedirs(self.localRepository)
      message                  = "just created"
    except OSError, e:
      if e.errno != errno.EEXIST:
        #Couldn't create the directory
        raise
      else:
        #Directory already existed
        message                = "already existent"  
    pass
    
    print("Local data repository (destination): %s (%s)" %(self.localRepository,message))    
  pass
  
  def downloadDirectoryWithFTP(self,address,filenames=None,namefilter=None):
    #Connect to the server
    if(address.find("ftp://")==0):
      serverAddress           = address.split("/")[2]
      directory               = "/"+"/".join(address.split("/")[3:])
    else:
      serverAddress           = address.split("/")[0]
      directory               = "/"+"/".join(address.split("/")[1:])
    pass

    #Open FTP session
    try:
      ftp                       = ftplib.FTP(serverAddress,"anonymous",'','',timeout=60)
    except socket.error as socketerror:
      raise GtBurstException(11,"Error when connecting: %s" % os.strerror(socketerror.errno))
    
    print("Loggin in to %s..." % serverAddress),
    try:
      ftp.login()
    except:
      #Maybe we are already logged in
      try:
        ftp.cwd('/')
      except:
        #nope! don't know what is happening
        raise
      pass
    pass
          
    print("done")
    self.makeLocalDir()
    try:
      ftp.cwd(directory)
    except:
      #Remove the empty directory just created
      try:
        os.rmdir(self.localRepository)
      except:
        pass
      raise GtBurstException(5,"The remote directory %s is not accessible. This kind of data is probably not available for trigger %s, or the server is offline." %(serverAddress+directory,self.trigName))      
    pass
    
    if(filenames==None):
      filenames                 = []
      ftp.retrlines('NLST', filenames.append)
    pass
    
    maxTrials                 = 10
    
    #Build the window for the progress
    if(self.parent==None):
      #Do not use any graphical output
      root                 = None
      m1                   = None
    else:
      #make a transient window
      root                 = Toplevel()
      root.transient(self.parent)
      root.grab_set()        
      l                    = Label(root,text='Downloading...')
      l.grid(row=0,column=0)
      m1                    = Meter(root, 500,20,'grey','blue',0,None,None,'white',relief='ridge', bd=3)
      m1.grid(row=1,column=0)
      m1.set(0.0,'Download started...')
      l2                    = Label(root,text='Total progress:')
      l2.grid(row=2,column=0)
      m2                    = Meter(root, 500,20,'grey','blue',0,None,None,'white',relief='ridge', bd=3)
      m2.grid(row=3,column=0)
      m2.set(0.0,'Download started...')
    pass
    
    for i,filename in enumerate(filenames):
      if(namefilter!=None and filename.find(namefilter)<0):
        #Filename does not match, do not download it
        continue
      
      if(root!=None):
        m2.set((float(i))/len(filenames))
      skip                    = False
      if(not self.getCSPEC):
        if(filename.find("cspec")>=0):
          skip                = True
      if(not self.getTTE):
        if(filename.find("tte")>=0):
          skip                = True
      if(not self.getRSP):
        if(filename.find("rsp")>=0):
          skip                = True
      if(not self.getCTIME):
        if(filename.find("ctime")>=0):
          skip                = True
      pass
      #if(filename.find(".pdf")>0 or filename.find("gif") >0 or filename.find(".png")>0):
      #  skip                  = (not self.minimal)
      if(skip):
        print("Skipping %s ..." %(filename))   
        continue
      else:
        print("Retrieving %s ..." %(filename)),
      
      if(root!=None):
        l['text']               = "Downloading %s..." % filename
      
      done                      = False
      local_filename          = os.path.join(self.localRepository,filename)
      
      while(done==False):        
        try:
          f                       = open(local_filename, 'wb')
        except:
          raise IOError("Could not open file %s for writing. Do you have write permission on %s?" %(local_filename,self.localRepository))
        
        g                         = downloadCallback.get_size()
        try:
          ftp.dir(filename,g)
          totalsize                 = g.size#*1024
          printer                   = downloadCallback.Callback(totalsize, f,m1)
          ftp.retrbinary('RETR '+ filename, printer)
          localSize                 = f.tell()
          f.close()
          if(localSize!=totalsize):
            #This will be catched by the next "except", which will retry
            raise
          done                = True
        except:
          print("\nConnection lost! Trying to reconnect...")
          #Reconnect
          f.close()
          try:
            ftp.close()
          except:
            pass
          ftp                 = ftplib.FTP(serverAddress,"anonymous",'','',timeout=60)
          try:
            ftp.login()
          except:
            pass
          ftp.cwd(directory)
          done                = False
          continue
        pass  
      print(" done")
    pass
    
    ftp.close()
    print("\nDownload files done!")
    if(root!=None):
      m2.set(1.0)
      root.destroy()
    pass
  pass
  
  def getFTP(self,errorCode=None,namefilter=None):
    #Path in the repository is [year]/bn[grbname]/current
    
    #Get the year
    year                      = "20%s" %(self.grbName[0:2])
    #trigger number
    triggerNumber             = "bn%s" %(self.grbName)
    
    remotePath                = "%s/%s/triggers/%s/%s/current" %(self.dataRepository,self.instrument,year,triggerNumber)
        
    self.downloadDirectoryWithFTP(remotePath,None,namefilter)
  pass
    
pass
