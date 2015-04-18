import urllib
import HTMLParser
import time
import re, os
import sys
from GtBurst.dataCollector import *
from GtBurst import dataHandling
from GtBurst.commands.gtllebin import gtllebin
from GtBurst.GtBurstException import *
import numpy
import pyfits
from GtBurst import html2text

#Set a global timeout of 10 seconds for all web connections
import socket
socket.setdefaulttimeout(60)

#Downloaded from 
#http://stackoverflow.com/questions/3276040/how-can-i-use-the-python-htmlparser-library-to-extract-data-from-a-specific-div
class DivParser(HTMLParser.HTMLParser):
  def __init__(self,desiredDivName):
    HTMLParser.HTMLParser.__init__(self)
    self.recording                      = 0
    self.data                           = []
    self.desiredDivName                 = desiredDivName

  def handle_starttag(self, tag, attributes):
    if tag != 'div':
      return
    if self.recording:
      self.recording                   += 1
      return
    for name, value in attributes:
      if name == 'id' and value == self.desiredDivName:
        break
    else:
      return
    self.recording                      = 1

  def handle_endtag(self, tag):
    if tag == 'div' and self.recording:
      self.recording                   -= 1

  def handle_data(self, data):
    if self.recording:
      self.data.append(data)
pass

class DownloadTransientData(dataCollector):
  def __init__(self,triggerName,dataRepository,localRepository,**kwargs):
    dataCollector.__init__(self,'lat',triggerName,dataRepository,localRepository,
                    True,True,True,True,**kwargs)
  pass
  
  def setCuts(self,ra,dec,roi,triggerTime,tstart,tstop,timetype='MET',strict=False):
    self.ra                   = float(ra)
    self.dec                  = float(dec)
    self.roi                  = float(roi)
    self.triggerTime          = float(triggerTime)
    self.tstart               = float(tstart)
    self.tstop                = float(tstop)
    self.timetype             = timetype
    
    #Retrieve the HTML page with the input mask, to get the maximum
    #time available in the server (this is needed for BA analysis)    
    temporaryFileName           = "__temp_query_result.html"
    try:
      os.remove(temporaryFileName)
    except:
      pass
    pass
    
    urllib.urlcleanup() 
    try:
      urllib.urlretrieve("http://fermi.gsfc.nasa.gov/cgi-bin/ssc/LAT/LATDataQuery.cgi",temporaryFileName)
    except socket.timeout:
      raise GtBurstException(11,"Time out when connecting to the server. Check your internet connection, or that you can access http://fermi.gsfc.nasa.gov, then retry")
    except:
      raise GtBurstException(1,"Problems with the download. Check your connection then retry")
    pass

    htmlFile                    = open(temporaryFileName)
    maxTimeLimit                = ''
    for line in htmlFile.readlines():
      res                       = re.findall('(.+)The event database currently holds [0-9]+ events, collected between (.+) UTC and (.+) UTC \(Mission Elapsed Time \(MET\) ([0-9]+) to ([0-9]+) seconds\)',
                                             line)
      if(len(res)!=0):
        #Found
        maxTimeLimit            = res[-1][-1]
        break
      pass
    pass
    htmlFile.close()
        
    os.remove(temporaryFileName)
    if(maxTimeLimit.replace(" ","")==''):
      raise GtBurstException(12,"The LAT data server is probably down for maintenance or loading new data. Check the page http://fermi.gsfc.nasa.gov/cgi-bin/ssc/LAT/LATDataQuery.cgi or retry later.")
    else:
      maxTimeLimit              = float(maxTimeLimit)
    pass
    
    if(maxTimeLimit < self.tstop):
      if(strict):
        #Fail
        raise GtBurstException(14,"The requested time limit %s is too large. Data are available up to %s." %(self.tstop,maxTimeLimit-1))
        return maxTimeLimit-1
      else:
        print("\n\nWARNING:The requested time limit %s is too large. Data are available up to %s. Will download up to %s.\n\n" %(self.tstop,maxTimeLimit-1,maxTimeLimit-1))
        self.tstop                = float(maxTimeLimit)-1
      pass
    pass
  pass
  
  def getFTP(self,what='Extended'):
    #Re-implementing this
    
    #This will complete automatically the form available at
    #http://fermi.gsfc.nasa.gov/cgi-bin/ssc/LAT/LATDataQuery.cgi
    #After submitting the form, an html page will inform about
    #the identifier assigned to the query and the time which will be
    #needed to process it. After retrieving the query number,
    #this function will wait for the files to be completed on the server,
    #then it will download them
    
    url                         = "http://fermi.gsfc.nasa.gov/cgi-bin/ssc/LAT/LATDataQuery.cgi"
    #Save parameters for the query in a dictionary
    parameters                  = {}
    parameters['coordfield']    = "%s,%s" %(self.ra,self.dec)
    parameters['coordsystem']   = "J2000"
    parameters['shapefield']    = "%s" %(self.roi)
    parameters['timefield']     = "%s,%s" %(self.tstart,self.tstop)
    parameters['timetype']      = "%s" %(self.timetype)
    parameters['energyfield']   = "30,1000000"
    parameters['photonOrExtendedOrNone'] = what
    parameters['destination']   = 'query'
    parameters['spacecraft']    = 'checked'
    
    print("Query parameters:")
    for k,v in parameters.iteritems():
      print("%30s = %s" %(k,v))
    
    #POST encoding    
    postData                    = urllib.urlencode(parameters)
    temporaryFileName           = "__temp_query_result.html"
    try:
      os.remove(temporaryFileName)
    except:
      pass
    pass
       
    urllib.urlcleanup()
    try:
      urllib.urlretrieve(url, 
                       temporaryFileName, 
                       lambda x,y,z:0, postData)
    except socket.timeout:
      raise GtBurstException(11,"Time out when connecting to the server. Check your internet connection, or that you can access http://fermi.gsfc.nasa.gov, then retry")
    except:
      raise GtBurstException(1,"Problems with the download. Check your connection or that you can access http://fermi.gsfc.nasa.gov, then retry.")
    pass
    
    #Now open the file, parse it and get the query ID
    htmlFile                    = open(temporaryFileName)
    lines                       = []
    for line in htmlFile:
      lines.append(line.encode('utf-8'))
    pass
    html                        = " ".join(lines).strip()
    htmlFile.close()
    print("\nAnswer from the LAT data server:\n")
    
    text                        = html2text.html2text(html.encode('utf-8').strip()).split("\n")
    
    if("".join(text).replace(" ","")==""):
      raise GtBurstException(1,"Problems with the download. Empty answer from the LAT server. Normally this means that the server is ingesting new data, please retry in half an hour or so.")
    text                        = filter(lambda x:x.find("[") < 0 and 
                                                  x.find("]") < 0 and 
                                                  x.find("#") < 0 and 
                                                  x.find("* ") < 0 and
                                                  x.find("+") < 0 and
                                                  x.find("Skip navigation")<0,text)
    text                        = filter(lambda x:len(x.replace(" ",""))>1,text)
    print "\n".join(text)
    print("\n\n")
    os.remove(temporaryFileName)
    if(" ".join(text).find("down due to maintenance")>=0):
      raise GtBurstException(12,"LAT Data server looks down due to maintenance.")
    
    parser                      = DivParser("sec-wrapper")
    parser.feed(html)
    
    if(parser.data==[]):
      parser                      = DivParser("right-side")
      parser.feed(html)
    pass
    
    try: 
      estimatedTimeLine           = filter(lambda x:x.find("The estimated time for your query to complete is")==0,parser.data)[0]
      estimatedTimeForTheQuery    = re.findall("The estimated time for your query to complete is ([0-9]+) seconds",estimatedTimeLine)[0]
    except:
      raise GtBurstException(1,"Problems with the download. Empty or wrong answer from the LAT server (see console). Please retry later.")
    pass
    
    httpAddress                 = filter(lambda x:x.find("http://fermi.gsfc.nasa.gov") >=0,parser.data)[0]
    
    #Now periodically check if the query is complete
    startTime                   = time.time()
    timeout                     = 1.5*max(5.0,float(estimatedTimeForTheQuery)) #Seconds
    refreshTime                 = 2.0  #Seconds
    #When the query will be completed, the page will contain this string:
    #The state of your query is 2 (Query complete)
    endString                   = "The state of your query is 2 (Query complete)"
    #Url regular expression
    regexpr                     = re.compile("wget (.*.fits)")
    
    #Build the window for the progress
    if(self.parent==None):
      #No graphical output
      root                 = None
    else:
      #make a transient window
      root                 = Toplevel()
      root.transient(self.parent)
      root.grab_set()
      l                    = Label(root,text='Waiting for the server to complete the query (estimated time: %s seconds)...' %(estimatedTimeForTheQuery))
      l.grid(row=0,column=0)
      m1                    = Meter(root, 500,20,'grey','blue',0,None,None,'white',relief='ridge', bd=3)
      m1.grid(row=1,column=0)
      m1.set(0.0,'Waiting...')
    pass
    
    links                       = None
    fakeName                    = "__temp__query__result.html"
    while(time.time() <= startTime+timeout):
      if(root!=None):
        if(estimatedTimeForTheQuery==0):
          m1.set(1)
        else:
          m1.set((time.time()-startTime)/float(max(estimatedTimeForTheQuery,1)))
      sys.stdout.flush()
      #Fetch the html with the results
      try:
        (filename, header)        = urllib.urlretrieve(httpAddress,fakeName)
      except socket.timeout:
        urllib.urlcleanup()
        if(root!=None):
          root.destroy()
        raise GtBurstException(11,"Time out when connecting to the server. Check your internet connection, or that you can access http://fermi.gsfc.nasa.gov, then retry")
      except:
        urllib.urlcleanup()
        if(root!=None):
          root.destroy()
        raise GtBurstException(1,"Problems with the download. Check your connection or that you can access http://fermi.gsfc.nasa.gov, then retry.")
      pass
      
      f                         = open(fakeName)
      html                      = " ".join(f.readlines())
      status                    = re.findall("The state of your query is ([0-9]+)",html)[0]
      #print("Status = %s" % status)
      if(status=='2'):
        #Get the download link
        links                   = regexpr.findall(html)
        break
      f.close()
      os.remove(fakeName)
      urllib.urlcleanup()
      time.sleep(refreshTime)
    pass
    
    if(root!=None):
      root.destroy()
    
    #Download the files
    #if(links!=None):
    #  for link in links:
    #    print("Downloading %s..." %(link))
    #    urllib.urlretrieve(link,link.split("/")[-1])
    #  pass
    #else:
    #  raise RuntimeError("Could not download LAT Standard data")
    #pass    
    remotePath                = "%s/%s/queries/" %(self.dataRepository,self.instrument)
    
    if(links!=None):
      filenames                 = map(lambda x:x.split('/')[-1],links)    
      try:
        self.downloadDirectoryWithFTP(remotePath,filenames=filenames)
      except Exception as e:
        #Try with "wget", if the system has it
        for ff in filenames:
          try:
            self.makeLocalDir()
            dataHandling.runShellCommand("wget %s%s -P %s" %("http://fermi.gsfc.nasa.gov/FTP/fermi/data/lat/queries/",ff,self.localRepository),True)
          except:
            raise e
          pass
        pass
      pass
    else:
      raise GtBurstException(1,"Could not download LAT Standard data")
    pass
    
    #Rename the files to something neater...
    newFilenames              = {}
    for f in filenames:
      #EV or SC?
      suffix                  = f.split("_")[1]
      if(suffix.find("EV")>=0):
        suffix                = 'ft1'
      elif(suffix.find("SC")>=0):
        suffix                = 'ft2'
      else:
        raise GtBurstException(13,"Could not understand the type of a downloaded file (%s)" %(f))
      newfilename             = os.path.join(self.localRepository,"gll_%s_tr_bn%s_v00.fit" %(suffix,self.grbName))
      localPath               = os.path.join(self.localRepository,f)
      
      os.rename(localPath,newfilename)
      newFilenames[suffix]    = newfilename
    pass
    
    ###########################
    if('ft1' in newFilenames.keys() and 'ft2' in newFilenames.keys()):
      dataHandling._makeDatasetsOutOfLATdata(newFilenames['ft1'],newFilenames['ft2'],
                                             self.grbName,self.tstart,self.tstop,
                                             self.ra,self.dec,self.triggerTime,
                                             self.localRepository,
                                             cspecstart=-1000,
                                             cspecstop=1000)
    
  pass
  
pass

