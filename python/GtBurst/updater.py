#!/usr/bin/env python

import urllib, os
from GtBurst.GtBurstException import GtBurstException
from GtBurst import getDataPath
import GtBurst
import md5

#Set a global timeout of 10 seconds for all web connections
import socket
socket.setdefaulttimeout(60)

remoteUrl = 'https://raw.githubusercontent.com/giacomov/gtburst/master/'

def update(debug=False):
  
  print("Searching updates at %s..." %(remoteUrl))
  
  #Download file_list file
  
  try:
  
    os.remove("__file_list")
  
  except:
  
    pass
  
  #now check if we have write permission in this directory
  try:
  
    with open("_write_test","w+") as f:
    
      f.write("TEST")
    
  except:
    
    raise GtBurstException(1,"The updater cannot write in directory %s. Do you have write permission there?" %(os.getcwd()))  
  
  else:
    
    os.remove("_write_test")
  
  urllib.urlcleanup()
  
  try:
  
    urllib.urlretrieve("%s/__file_list" % remoteUrl, "__file_list")
  
  except socket.timeout:
  
    raise GtBurstException(11,"Time out when connecting to %s. Check your internet connection, then retry" % (remoteUrl))
  
  except:
  
    raise GtBurstException(1,"Problems with the download. Check your connection, and that you can reach %s" %(remoteUrl))
  
  pass  
    
  #Read the list of files
  f                           = open('__file_list')
  files                       = f.readlines()
  f.close()
  os.remove("__file_list")
  
  #Check if there is a HTML tag in the __file_list. This can
  #happen if there is a proxy in between which is forwarding to
  #a page different than the one intended
  if(" ".join(files).lower().find("<html>") >= 0):
    raise GtBurstException(1,"Download was redirected. This happens usually when you are behind a proxy." +
                             " If you are behind a proxy, make sure to log in and " +
                             "that executables from the command line can reach the internet directly.")
   
  #Get the path of the gtburst installation
  path                      = GtBurst.__file__
  installationPath          = os.path.join(os.path.sep.join(path.split(os.path.sep)[0:-3]))
  
  dataPath                  = getDataPath.getDataPath()
  
  nUpdates                  = 0
  for ff in files:
    atoms                     = ff.split()
    pathname                  = atoms[-1].replace('*','')
    if(ff.find("__file_list")>=0):
      if(debug):
        print("Skipping %s..." %(ff))
    else:
      remoteMD5                    = atoms[0]
      if(debug):
        print("File %s has remote MD5 checksum %s" %(pathname,remoteMD5))
      
      #Check if the file exists in the local installation
      pathnameThisSys         = pathname.replace("/",os.path.sep)
      
      if(pathname.find("data")==0):
        
        #This is a data file
        localPath             = os.path.join(dataPath,pathnameThisSys.replace("data%s" % (os.path.sep),""))
      
      else:
      
        #This is some other file
        localPath             = os.path.join(installationPath,pathnameThisSys)
      
      pass
      
      if(not os.path.exists(localPath)):
        print("File %s does not exist in the current installation. Creating it..." %(localPath))
        #If the new file is in a new directory, the directory needs to be created
        try:
          os.makedirs(os.path.dirname(localPath))
        except:
          #This will fail if the directory already exists
          pass
        downloadFile(pathname,localPath)
        nUpdates              += 1
      else:
        #File exists. Check the size
        localMD5             = md5.md5(open(localPath, 'rb').read()).hexdigest()
        if(localMD5!=remoteMD5):
          print("Updating %s..." %(localPath))
          downloadFile(pathname,localPath)
          nUpdates              += 1
        else:
          if(debug):
            print("NOT updating %s (local MD5: %s, remote MD5: %s)..." %(localPath,localMD5,remoteMD5))
          pass
        pass
        if(debug):
          print("\n\n")
    pass
  pass
  
  return nUpdates
pass

def downloadFile(remotepathname,localpathname):
  try:
    urllib.urlretrieve("%s/%s" % (remoteUrl, remotepathname),localpathname)
  except socket.timeout:
    raise GtBurstException(11,"Time out. Check your internet connection, and that you can access %s, then retry" % (remoteUrl))
  except:
    raise GtBurstException(1,"Problems with the download. Check your connection, and that you can reach %s, then retry" %(remoteUrl))
  pass
  
