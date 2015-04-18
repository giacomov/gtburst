#Author:
# G.Vianello (giacomov@slac.stanford.edu, giacomo.slac@gmail.com)

import UnbinnedAnalysis
import BinnedAnalysis

import numpy
import os,sys, re, glob, shutil, datetime, time
import pyfits
import math
import pywcs
from GtApp import GtApp
import scipy.optimize
import warnings
import xml.etree.ElementTree as ET
import multiprocessing
import subprocess
from contextlib import contextmanager

from GtBurst import LikelihoodComponent
from GtBurst import IRFS
from GtBurst.statMethods import *
from GtBurst.Configuration import Configuration
from GtBurst.GtBurstException import GtBurstException
from GtBurst.commands.gtllebin import gtllebin
from GtBurst import version
from GtBurst import angularDistance

#Use a backend which does not require a running X server,
#so commands will be able to run in batch mode
#(Note that this call is uneffective when dataHandling is imported
#from the GUI, since the GUI has its own .use() call)
import matplotlib
matplotlib.use('Agg',False)

import matplotlib.pyplot as plt
matplotlib.rcParams['font.size'] = 8

#Version tag
moduleVersion                 = version.getVersion()

#Definitions
eventsExtName                 = "EVENTS"
cspecExtName                  = "SPECTRUM"
eboundsExtName                = "EBOUNDS"
emin_column                   = "E_MIN"
emax_column                   = "E_MAX"

#Systematic error for each channel in the background spectrum
BACK_SYS_ERROR                = 0.03

#Optimizer
optimizer                     = "DRMNFB"

#This are made so that bin(33) give a bit mask compatible with a transient event
simirfs                       = {}
simirfs['transient']          = 33
simirfs['TRANSIENT']          = 33
simirfs['P7TRANSIENT_V6']     = 33
simirfs['source']             = 37
simirfs['SOURCE']             = 37
simirfs['P7SOURCE_V6']        = 37

#Predefined projection for sky maps
projection                    = 'AIT'

_missionStart = datetime.datetime(2001, 1, 1, 0, 0, 0)
_century = 2000

@contextmanager
def suppress_output(suppress_stderr=True,suppress_stdout=False):
    # Open a pair of null files
    null_fds                  =  [os.open(os.devnull,os.O_RDWR | os.O_EXCL) for x in range(2)]
    
    # Save the actual stdout (1) and stderr (2) file descriptors.
    save_fds                  = (os.dup(1), os.dup(2))
    
    # Assign the null pointers to stdout and stderr.
    if(suppress_stdout):
      os.dup2(null_fds[0],1)
    
    if(suppress_stderr):
      os.dup2(null_fds[1],2)
    
    try:
      #This is where the body of the "with" statement get executed
      yield    
    finally:
      # Re-assign the real stdout/stderr back to (1) and (2)
      if(suppress_stdout):
        os.dup2(save_fds[0],1)
      
      if(suppress_stderr):
        os.dup2(save_fds[1],2)
      
      # Close the null files
      os.close(null_fds[0])
      os.close(null_fds[1])      
    
pass

def exceptionPrinter(msg,exceptionText):
    sys.stderr.write("-------------- EXCEPTION ---------------------------\n")
    sys.stderr.write("\n%s\n" % msg)
    sys.stderr.write("\n%s\n" % exceptionText)
    sys.stderr.write("-------------- EXCEPTION ---------------------------\n")      


def getLATdataFromDirectory(directory):
    cspecFiles                = glob.glob(os.path.join(os.path.abspath(directory),"gll_cspec_tr_*.pha"))
    if(len(cspecFiles)==0):
      print("No data available in directory %s." %(os.path.abspath(directory)))
      return None
    pass
    
    if(len(cspecFiles)>1):
      raise RuntimeError("More than one LAT CSPEC file in %s" %(os.path.abspath(directory)))
    else:
      cspecFile               = cspecFiles[0]
    pass
    
    filename                  = os.path.abspath(os.path.expanduser(cspecFile))
    directory                 = os.path.dirname(os.path.abspath(filename))
    
    #Transient data
    rootName                  = "_".join(os.path.basename(filename).split("_")[2:5]).split(".")[:-1]
    rootName                  = ".".join(rootName)

    detector                  = "LAT"
    trigger                   = rootName.split("_")[1]
            
    triggered                 = True
    triggerTime               = getTriggerTime(filename)
    dataset                   = {}
    dataset['eventfile']      = os.path.join(directory,"gll_ft1_%s.fit" %(rootName))
    dataset['ft2file']        = os.path.join(directory,"gll_ft2_%s.fit" %(rootName))
    dataset['rspfile']        = os.path.join(directory,"gll_cspec_%s.rsp" %(rootName))
    dataset['cspecfile']      = cspecFile
    #Check that they actually exists
    for k,v in dataset.iteritems():
      if(not os.path.exists(v)):
        raise RuntimeError("Datafile %s (%s) does not exists! Corrupted dataset..." %(v,k))
      pass
    pass
    return dataset


def getPointing(triggertime,ft2,bothAxes=False):
  f                       = pyfits.open(ft2)
  data                    = f['SC_DATA'].data
  #Find first element after trigger time in FT2 file
  idx_after               = numpy.searchsorted(numpy.sort(data.START),triggertime)
  idx_before              = idx_after-1
  if(idx_after==len(data) or idx_before < 0):
    raise RuntimeError("Provided FT2 file do not cover enough time")
  f.close()
  
  #Now interpolate linearly between the position of the z-axis before and after the trigger time,
  #which is needed if we are using 30 s FT2 file (otherwise the position could be off by degrees)
  ra_scz                  = numpy.interp(0,[data.START[idx_before]-triggertime,data.START[idx_after]-triggertime],[data.RA_SCZ[idx_before],data.RA_SCZ[idx_after]])
  dec_scz                 = numpy.interp(0,[data.START[idx_before]-triggertime,data.START[idx_after]-triggertime],[data.DEC_SCZ[idx_before],data.DEC_SCZ[idx_after]])
  
  if(bothAxes):
    ra_scx                = numpy.interp(0,[data.START[idx_before]-triggertime,data.START[idx_after]-triggertime],[data.RA_SCX[idx_before],data.RA_SCX[idx_after]])
    dec_scx               = numpy.interp(0,[data.START[idx_before]-triggertime,data.START[idx_after]-triggertime],[data.DEC_SCX[idx_before],data.DEC_SCX[idx_after]])
    return ra_scz, dec_scz, ra_scx, dec_scx
  else:
    return ra_scz, dec_scz
pass

def makeNavigationPlots(ft2file,ra_obj,dec_obj,triggerTime):
    ft2                       = pyfits.open(ft2file)
    ra_scz                    = ft2['SC_DATA'].data.field("RA_SCZ")
    dec_scz                   = ft2['SC_DATA'].data.field("DEC_SCZ")
    ra_zenith                 = ft2['SC_DATA'].data.field("RA_ZENITH")
    dec_zenith                = ft2['SC_DATA'].data.field("DEC_ZENITH")
    time                      = ft2['SC_DATA'].data.field("START")
    time                      = numpy.array(map(lambda x:x-triggerTime,time))
    ft2.close()
        
    zenith                    = map(lambda x:angularDistance.getAngularDistance(x[0],x[1],ra_obj,dec_obj),zip(ra_zenith,dec_zenith))
    zenith                    = numpy.array(zenith)
    theta                     = map(lambda x:angularDistance.getAngularDistance(x[0],x[1],ra_obj,dec_obj),zip(ra_scz,dec_scz))
    theta                     = numpy.array(theta)    

    
    #mask out data gaps do they will appear as gaps in the plots
    mask                      = (time-numpy.roll(time,1) > 40.0)
    for idx in mask.nonzero()[0]:
      time                    = numpy.insert(time,idx,time[idx-1]+1)
      zenith                  = numpy.insert(zenith,idx,numpy.nan)
      theta                   = numpy.insert(theta,idx,numpy.nan)
      time                    = numpy.insert(time,idx+1,time[idx+1]-1)
      zenith                  = numpy.insert(zenith,idx+1,numpy.nan)
      theta                   = numpy.insert(theta,idx+1,numpy.nan)
    pass
    
    figure                    = plt.figure(figsize=[4,4],dpi=150)
    figure.set_facecolor("#FFFFFF")
    figure.suptitle("Navigation plots")
    #Zenith plot
    subpl1                    = figure.add_subplot(211)    
    subpl1.set_xlabel("Time since trigger (s)")
    subpl1.set_ylabel("Source Zenith angle (deg)")
    subpl1.set_ylim([min(zenith-12)-0.1*min(zenith-12),max([max(zenith+20),130])])
    subpl1.plot(time,zenith,'--',color='blue')
    msk                       = numpy.isnan(zenith)
    stdidx                    = 0

    try:
      for idx in msk.nonzero()[0][::2]:
          subpl1.fill_between(time[stdidx:idx],zenith[stdidx:idx]-15,zenith[stdidx:idx]+15,
                              color='gray',alpha=0.5,label='15 deg ROI')
          subpl1.fill_between(time[stdidx:idx],zenith[stdidx:idx]-12,zenith[stdidx:idx]+12,
                              color='lightblue',alpha=0.5, label='12 deg ROI')
          subpl1.fill_between(time[stdidx:idx],zenith[stdidx:idx]-10,zenith[stdidx:idx]+10,
                              color='green',alpha=0.5, label='10 deg ROI')
          stdidx                = idx+2
      pass
      subpl1.fill_between(time[stdidx+1:],zenith[stdidx+1:]-15,zenith[stdidx+1:]+15,
                              color='gray',alpha=0.5,label='15 deg ROI')
      subpl1.fill_between(time[stdidx+1:],zenith[stdidx+1:]-12,zenith[stdidx+1:]+12,
                              color='lightblue',alpha=0.5, label='12 deg ROI')
      subpl1.fill_between(time[stdidx+1:],zenith[stdidx+1:]-10,zenith[stdidx+1:]+10,
                              color='green',alpha=0.5, label='10 deg ROI')
    except:
      subpl1.fill_between(time,zenith-15,zenith+15,
                              color='gray',alpha=0.5,label='15 deg ROI')
      subpl1.fill_between(time,zenith-12,zenith+12,
                              color='lightblue',alpha=0.5, label='12 deg ROI')      
      subpl1.fill_between(time,zenith-10,zenith+10,
                              color='green',alpha=0.5, label='10 deg ROI')
    tt3 = subpl1.axhline(100,color='red',linestyle='--')
    p1 = plt.Rectangle((0, 0), 1, 1, color="green",alpha=0.5)
    p2 = plt.Rectangle((0, 0), 1, 1, color="lightblue",alpha=0.5)
    p3 = plt.Rectangle((0, 0), 1, 1, color="gray",alpha=0.5)
    zl = subpl1.axhline(1000,color='blue',linestyle='--')
    subpl1.legend([zl,tt3,p1,p2,p3],
                  ["Source",'Zenith = 100 deg',"10 deg ROI","12 deg ROI","15 deg ROI"],
                  prop={'size':5},ncol=2)
    
    #Theta plot
    subpl2                    = figure.add_subplot(212,sharex=subpl1)   
    subpl2.set_xlabel("Time since trigger (s)")
    subpl2.set_ylabel("Source off-axis angle (deg)")
    subpl2.set_ylim([min(theta)-0.1*min(theta),max([max(theta),95])])
    subpl2.plot(time,theta,'--')
    subpl2.axhline(65,color='r',linestyle='--')
    return figure
pass

def testIfExecutableExists(program):
    import os
    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

    return None

def runShellCommand(string,echo=False):
  if(echo):
    print("\n%s\n" % string)
  #This is to substitute os.system, which is not working well
  #in the ipython notebook
  try:
    retcode = subprocess.call(string, shell=True)
    if retcode < 0:
        print >>sys.stderr, "Child was terminated by signal", -retcode
    else:
        pass
  except OSError, e:
    print >>sys.stderr, "Execution failed:", e
pass

def date2met(*kargs):
    datestring = kargs[0]
    
    if not isinstance(datestring,str):
        if not isinstance(datestring,float): print "date2met: Single argument needs to be a string of the format 2008-05-16 00:00:00 or 2008/05/16 00:00:00"
        raise ValueError
    
    sep='-'
    if '/' in datestring : sep='/'
    year,month,day=datestring.split(sep)
    if len(year)==2: year=int(year)+_century
    time   = 0.0
    decsec = 0.0
    
    try:
        # time given in the string?
        day = day.replace(' ',':')
        day,hours,mins,secs=day.split(':')
        secs=float(secs)
        secs_i = math.floor(secs)
        decsec = secs-secs_i
        current = datetime.datetime(year=int(year),month=int(month),day=int(day),hour=int(hours),minute=int(mins),second=int(secs_i))
    except ValueError:
        try:
            # time given in second of day as a second argument?
            time=int(kargs[1])
        except:
            pass
        current = datetime.datetime(int(year), int(month), int(day), 0,0,0)
        pass
    diff = current -_missionStart
    met= diff.days*86400. + diff.seconds + time + decsec
    if float(year)>2005:    met+=1
    if float(year)>2008:    met+=1
    if float(met)>362793601.0: met+=1 # June 2012 leap second    
    return met


def met2date(MET,opt=None):
    """
    converts a MET time into a date string, in format \"08-07-25 10:26:09\".
    If opt=="grbname", the GRB name format 080725434 is returned. 
    """

    if MET>252460801:   MET=MET-1
    if MET>156677800:   MET=MET-1
    if MET>362793601:   MET=MET-1 # 2012 leap second
    
    metdate  = datetime.datetime(2001, 1, 1,0,0,0)
    dt=datetime.timedelta(seconds=float(MET))
    grb_date=metdate + dt
    yy=grb_date.year
    mm=grb_date.month
    dd=grb_date.day
    hr=grb_date.hour
    mi=grb_date.minute
    #ss=grb_date.second
    ss=round(grb_date.second+grb_date.microsecond*1e-6)        
    fff=round(float(ss+60.*mi+3600.*hr)/86.4)
    if fff>999: fff=999
    d0=datetime.datetime(int(yy), 1,1,0,0,0)
    doy=(grb_date-d0).days+1
    try:
        if (opt.upper()=="GRBNAME" or opt.upper()=="NAME"):
            return '%02i%02i%02i%03i' %(yy-_century,mm,dd,fff)
        elif (opt.upper()=='FFF'):
            return grb_date,fff
        pass
    except:
        pass
    text='%04d-%02d-%02d %02d:%02d:%02d (DOY:%03s)' %(yy,mm,dd,hr,mi,ss,doy)
    return text


def _getLatestVersion(filename):
    #Looks in the directory for the latest version of the file filename
    #filename is something like gll_lle_bn100724029_v00.fit or glg_cspec_n0_bn100724029_v00.fit
    #This method looks for the file with the same name but the greatest v?? version
    directory                 = os.path.dirname(filename)
    filename                  = os.path.basename(filename)
    
    regExp                    = "(.+)(_v[0-9]{2})\.(.+)"
    m                         = re.search(regExp,filename)
    
    #This is something like "glg_tte_bn100724029" or "glg_tte_n0_bn100724029"
    rootName                  = m.group(1)
    oldVersion                = m.group(2).replace("_","")
    extension                 = m.group(3)
    
    fileList                  = glob.glob(os.path.join(directory,"%s_v*.%s" %(rootName,extension)))
    #Get the versions
    matches                   = map(lambda x:re.search(regExp,x),fileList)
    matches                   = filter(lambda x:x!=None,matches)

    if(len(matches)==0):
      raise RuntimeError("No version found for file of type %s. Does the directory contain data?" %("%sv*.%s" %(rootName,extension)))
    
    versions                  = map(lambda x:int(x.group(2)[2:]),matches)
    #Get the position of the maximum
    idx                       = versions.index(max(versions))
    #Get the most recent version of the file and return it
    return os.path.join(directory,fileList[idx])
pass


def getIsotropicTemplateNormalization(xmlmodel):
  tree                        = ET.parse(xmlmodel)
  root                        = tree.getroot()
  norm                        = None
  for source in root.findall('source'):
    if(source.get('name')=='IsotropicTemplate'):
      spectrum                = source.findall('spectrum')[0]
      param                   = spectrum.findall('parameter')[0]
      norm                    = float(param.get('value'))
    pass
  pass
  return norm
pass

def setIsotropicTemplateNormalization(xmlmodel,value):
  tree                        = ET.parse(xmlmodel)
  root                        = tree.getroot()
  for source in root.findall('source'):
    if(source.get('name')=='IsotropicTemplate'):
      spectrum                = source.findall('spectrum')[0]
      param                   = spectrum.findall('parameter')[0]
      param.set('value',"%s" % value)
    pass
  pass
  f                         = open(xmlmodel,'w+')
  tree.write(f)
  f.close()
pass

def multiplyIsotropicTemplateFluxSim(xmlsimmodel,factor):
  tree                        = ET.parse(xmlsimmodel)
  root                        = tree.getroot()
  for source in root.findall('source'):
    if(source.get('name')=='IsotropicTemplate'):
      spectrum                = source.findall('spectrum')[0]
      spectrumClass           = spectrum.findall('SpectrumClass')[0]
      oldparams               = spectrumClass.get('params')
      before,after            = oldparams.split("flux=")
      oldflux                 = float(after.split(",")[0])
      newflux                 = oldflux*float(factor)
      newparams               = oldparams.replace("flux=%s" %(after.split(",")[0]),"flux=%s" %(newflux))
      spectrumClass.set('params'," ".join(newparams.split()))
    pass
  pass
  f                         = open(xmlsimmodel,'w+')
  tree.write(f)
  f.close()  
pass

def removePointSource(xmlinput,xmloutput,sourceName):
  tree                        = ET.parse(xmlinput)
  root                        = tree.getroot()
  for source in root.findall('source'):
    if(source.get('name')==sourceName):
      root.remove(source)
    pass
  pass
  f                         = open(xmloutput,'w+')
  tree.write(f)
  f.close()  
pass

def _makeDatasetsOutOfLATdata(ft1,ft2,grbName,tstart,tstop,
                              ra,dec,triggerTime,localRepository='.',
                              cspecstart=None,cspecstop=None):
    
    #FIX tstart and tstop
    ra                        = float(ra)
    dec                       = float(dec)
    triggerTime               = float(triggerTime)
    tstart                    = float(tstart)+int(float(tstart) < 231292801.000)*triggerTime
    tstop                     = float(tstop)+int(float(tstop) < 231292801.000)*triggerTime
    
    if(cspecstart==None):
      cspecstart              = tstart
    if(cspecstop==None):
      cspecstop               = tstop
    
    cspecstart                = float(cspecstart)+int(float(cspecstart) < 231292801.000)*triggerTime
    cspecstop                 = float(cspecstop)+int(float(cspecstop) < 231292801.000)*triggerTime
    
    if(grbName.find('bn')==0):
      grbName                 = grbName[2:]
    
    #Generate a fake response file to define the energy binning for the CSPEC file
    ebounds                   = numpy.logspace(numpy.log10(100),numpy.log10(300000),3)
    emins                     = numpy.array(ebounds[:-1])
    emaxs                     = numpy.array(ebounds[1:])
    emins_column              = pyfits.Column(name='E_MIN', format='E', array=emins)
    emaxs_column              = pyfits.Column(name='E_MAX', format='E', array=emaxs)
    cols                      = pyfits.ColDefs([emins_column, emaxs_column])
    tbhdu                     = pyfits.new_table(cols)
    tbhdu.header.set('EXTNAME','EBOUNDS')
    hdu                       = pyfits.PrimaryHDU(None)
    fakematrixhdu             = pyfits.new_table(pyfits.ColDefs([pyfits.Column(name="FAKE",format='E')]))
    fakematrixhdu.header.set('EXTNAME',"SPECRESP MATRIX")
    eboundsFilename           = os.path.join(localRepository,"gll_cspec_tr_bn%s_v00.rsp" %(grbName))
    thdulist                  = pyfits.HDUList([hdu, tbhdu, fakematrixhdu])
    print("Writing %s..." %(eboundsFilename))
    thdulist.writeto(eboundsFilename,clobber='yes')
    
    #Produce a CSPEC file with LAT Transient data
    
    #Select a 15 deg ROI around the ra,dec
    gtselect                  = GtApp('gtselect')
    gtselect['infile']        = ft1
    tempName                  = '__temp_ft1.fits'
    gtselect['outfile']       = tempName
    gtselect['ra']            = float(ra)
    gtselect['dec']           = float(dec)
    gtselect['rad']           = 15.0
    gtselect['tmin']          = cspecstart-1.0
    gtselect['tmax']          = cspecstop+1.0
    gtselect['emin']          = 10.0
    gtselect['emax']          = 300000.0
    gtselect['zmax']          = 110.0
    gtselect['clobber']       = 'yes'
    gtselect.run()
    
    
    cspecfile                 = os.path.join(localRepository,"gll_cspec_tr_bn%s_v00.pha" %(grbName))
    parameters                = {}
    parameters['eventfile']   = tempName
    parameters['rspfile']     = eboundsFilename
    parameters['ft2file']     = ft2
    parameters['dt']          = 1.024*4
    parameters['tstart']      = cspecstart
    parameters['tstop']       = cspecstop
    parameters['cspecfile']   = cspecfile
    parameters['clobber']     = 'yes'
    print("Writing %s..." %(cspecfile))
    gtllebin(**parameters)
    
    try:
      os.remove(tempName)
    except:
      pass
    pass
    updateKeywords(ft1,triggerTime,ra,dec,grbName)
    updateKeywords(ft2,triggerTime,ra,dec,grbName)
    updateKeywords(cspecfile,triggerTime,ra,dec,grbName)
    updateKeywords(eboundsFilename,triggerTime,ra,dec,grbName)
    
    return ft1,eboundsFilename,ft2,cspecfile
pass

def updateKeywords(filename,triggerTime,ra,dec,grbName):
  #Now update some keywords in the ft1 file
  ft1                       = pyfits.open(filename,'update')
  for i in range(len(ft1)):
    ft1[i].header.set("TRIGTIME",triggerTime)
    ft1[i].header.set("RA_OBJ",ra)
    ft1[i].header.set("DEC_OBJ",dec)
    ft1[i].header.set("OBJECT",grbName)
  pass
  ft1.close()
pass

def _writeParamIntoXML(xmlmodel,**pardict):
  f                           = open(xmlmodel,'a')
  
  for key,value in pardict.iteritems():
    f.write("\n<!-- %s=%s -->" %(key.upper(),value))
  pass
  
  f.close()
pass

def _getParamFromXML(xmlmodel,parname):
  #Get the parval
  f                           = open(xmlmodel,'r')
  parval                      = None
  for line in f.readlines():
    if(line.find("%s=" %parname)>=0 and line.find("<!--")>=0):
      parval                     = re.findall('<!-- %s=(.+) -->' %(parname),line)[0]
  pass
  f.close()
  return parval
pass

def _fileExists(filename):
  try:
    with open(os.path.expanduser(filename)) as f:
      return True
  except IOError as e:
    return False
pass

def _getAbsPath(filename):
  return os.path.abspath(os.path.expanduser(filename))
pass

def _getIterable(obj):
  '''
  If obj is not iterable, this method encapsulate it in a list and return such a list
  '''
  try:
      dumb                    = len(obj)
      return obj
  except:
      inList                  = [obj]
      return inList  
  pass
pass  

def getTriggerTime(ff):
  f                             = pyfits.open(os.path.abspath(os.path.expanduser(ff)))
  if("UREFTIME" in f[0].header.keys()):
    trigTime                    = f[0].header['UREFTIME']
  elif("TRIGTIME" in f[0].header.keys()):
    trigTime                    = f[0].header['TRIGTIME']
  else:  
    trigTime                    = -1
    for extname in [cspecExtName,eventsExtName,'SPECRESP MATRIX','MATRIX']:
      try:
        trigTime                = f[extname,1].header['TRIGTIME']
        break
      except:
        continue
      pass
    pass      
  pass
  f.close()
  return float(trigTime)
pass

class LLEData(object):
  def __init__(self,eventFile,rspFile,ft2File,root=None):
    #Avoid the unicode problem by casting it to integer
    eventFile                 = str(eventFile)
    rspFile                   = str(rspFile)
    ft2File                   = str(ft2File)
    
    #Check that the file exists
    
    if(not _fileExists(eventFile)):
      raise IOError("File %s does not exist!" %(eventFile))
    pass
    
    self.eventFile            = _getAbsPath(eventFile)
    self.originalEventFile    = self.eventFile
    
    if(not _fileExists(rspFile)):
      raise IOError("File %s does not exist!" %(rspFile))
    pass
    self.rspFile              = _getAbsPath(rspFile)
    
    self.isGBM                = False
    if(not _fileExists(ft2File)):
      #If these are GBM data files, it's ok!
      #open tteFile
      f                       = pyfits.open(self.eventFile)
      instrument              = f[0].header['INSTRUME']
      if(instrument.upper().find('GBM')>=0):
        self.isGBM            = True
      else:
        f.close()
        raise IOError("File %s does not exist!" %(ft2File))
      pass
      f.close()
    pass
        
    if(self.isGBM):
      self.ft2File            = 'None'
    else:  
      self.ft2File            = _getAbsPath(ft2File)
    pass
    
    #Get informations
    self.__readHeader()
    
    if(root==None):
        self.rootName         = ".".join(os.path.basename(self.eventFile).split(".")[0:-1])
    else:
        self.rootName         = str(root)
    pass
    
    self.gtbin                = GtApp('gtbin')
    self.gtselect             = GtApp('gtselect')
    self.gtbindef             = GtApp('gtbindef')
  pass
  
  def __readHeader(self):
    #Get informations from the header of the file,
    #and fill attributes of the class
    
    self.trigTime             = getTriggerTime(self.rspFile)
    
    f                         = pyfits.open(self.eventFile)
    try:
      header                  = f[eventsExtName].header
      self.isTTE              = True
    except:
      header                  = f[cspecExtName].header
      self.isTTE              = False
    pass
      
    self.tstart               = header['TSTART']
    self.tstop                = header['TSTOP']
    try:
      self.object             = header['OBJECT']
    except:
      self.object             = "UNKN-OBJECT"
    try:
      self.telescope          = header['TELESCOP']
    except:
      self.telescope          = "UNKN-TELESCOPE"
    try:
      self.instrument         = header['INSTRUME']
    except:
      self.instrument         = "UNKN-INSTRUME"    
    f.close()
  pass
  
  def _selectByTime(self,t1,t2,outfile):
    if(not self.eventFile):
      raise RuntimeError("You cannot select by time if you don't provide a TTE/LLE/FT1 file.")
    self.gtselect['infile']   = self.eventFile
    self.gtselect['outfile']  = outfile
    self.gtselect['ra']       = "INDEF"
    self.gtselect['dec']      = "INDEF"
    self.gtselect['rad']      = "INDEF"
    self.gtselect['tmin']     = float(t1)+int(float(t1) < 231292801.000)*self.trigTime
    self.gtselect['tmax']     = float(t2)+int(float(t2) < 231292801.000)*self.trigTime
    self.gtselect['emin']     = 0
    self.gtselect['emax']     = 0
    self.gtselect['zmax']     = 180
    self.gtselect['evclass']  = "INDEF"
    self.gtselect['convtype'] = -1
    self.gtselect['clobber']  = "yes"
    self.gtselect.run()
  pass
  
  def _writeEnergyBinFile(self,outfile):
    #Take the energy binning from the response matrix,
    #to ensure combatibility
    rsp                       = pyfits.open(self.rspFile)
    ebounds                   = rsp[eboundsExtName].data
    
    asciiFilename             = "__ebins.txt"
    asciiFile                 = open(asciiFilename,"w+")
    
    for emin,emax in zip(ebounds.field(emin_column),ebounds.field(emax_column)):
      asciiFile.write("%20.10f %20.10f\n" %(emin,emax))
    pass
    
    asciiFile.close()
    
    rsp.close()
    
    self.gtbindef['bintype']  = "E"
    self.gtbindef['binfile']  = asciiFilename
    self.gtbindef['outfile']  = outfile
    self.gtbindef['energyunits'] = "keV"
    self.gtbindef['clobber']  = "yes"
    self.gtbindef.run()
    
    os.remove(asciiFilename)
  pass
  
  def binByEnergy(self,t1,t2,outfile):
    
    #Ensure that t1 and t2 are float
    try:
      t1                      = float(t1)+int(float(t1) < 231292801.000)*self.trigTime
    except:
      raise ValueError("t1 is not a valid starting time")
    pass
    
    try:
      t2                      = float(t2)+int(float(t2) < 231292801.000)*self.trigTime
    except:
      raise ValueError("t2 is not a valid starting time")
    pass    
    
    tempfile                  = "__dhselEvt.fits"
    self._selectByTime(t1,t2,tempfile)
    
    #Write energy bin file
    energyBinsFile            = "__energyBins.fits"
    self._writeEnergyBinFile(energyBinsFile)
    
    self.gtbin['evfile']      = tempfile
    self.gtbin['scfile']      = self.ft2File
    self.gtbin['outfile']     = outfile
    self.gtbin['algorithm']   = "PHA1"
    self.gtbin['ebinalg']     = "FILE"
    self.gtbin['ebinfile']    = energyBinsFile
    self.gtbin['clobber']     = "yes"
    self.gtbin.run()
    
    os.remove(tempfile)
    os.remove(energyBinsFile)
  pass
  
  def binByEnergyAndTime(self,*args):
    if(len(args)==4):
      self._binByEnergyAndTimeLinear(*args)
    elif(len(args)==2):
      self._binByEnergyAndTimeFile(*args)
    else:
      raise RuntimeError("Wrong number of arguments")    
  pass
  
  def _binByEnergyAndTimeLinear(self,t1,t2,binsize,outfile): 
    #Ensure that t1 and t2 are float
    try:
      t1                      = float(t1)+int(float(t1) < 231292801.000)*self.trigTime
    except:
      raise ValueError("t1 is not a valid start time")
    pass
    
    try:
      t2                      = float(t2)+int(float(t2) < 231292801.000)*self.trigTime
    except:
      raise ValueError("t2 is not a valid stop time")
    pass
        
    #Write energy bin file
    energyBinsFile            = "__energyBins.fits"
    self._writeEnergyBinFile(energyBinsFile)
    
    self.gtbin['evfile']      = self.eventFile
    self.gtbin['scfile']      = self.ft2File
    self.gtbin['outfile']     = outfile
    self.gtbin['algorithm']   = "PHA2"
    self.gtbin['ebinalg']     = "FILE"
    self.gtbin['ebinfile']    = energyBinsFile
    self.gtbin['tbinalg']     = "LIN"
    self.gtbin['tstart']      = t1
    self.gtbin['tstop']       = t2
    self.gtbin['dtime']       = binsize
    self.gtbin['chatter']     = 1
    self.gtbin['clobber']     = "yes"
    self.gtbin.run()
    
    os.remove(energyBinsFile)
  pass

  def _binByEnergyAndTimeFile(self,timeBinsFile,outfile):     
    if(self.isTTE):
      #Write energy bin file
      energyBinsFile            = "__energyBins.fits"
      self._writeEnergyBinFile(energyBinsFile)
      self.gtbin['evfile']      = self.eventFile
      self.gtbin['scfile']      = self.ft2File
      self.gtbin['outfile']     = outfile
      self.gtbin['algorithm']   = "PHA2"
      self.gtbin['ebinalg']     = "FILE"
      self.gtbin['ebinfile']    = energyBinsFile
      self.gtbin['tbinalg']     = "FILE"
      self.gtbin['tbinfile']    = timeBinsFile
      #Need to set this otherwise gtbin will throw a "TSTART must be before than TSTOP!"
      #exception
      self.gtbin['tstart']      = -1
      self.gtbin['tstop']       = 0  
      self.gtbin['clobber']     = "yes"
      self.gtbin.run()
      os.remove(energyBinsFile)
      return
    else:
      #Rebin the CSPEC
      
      #Open the CSPEC
      cspec                   = pyfits.open(self.eventFile)
      channelsEmin            = cspec["EBOUNDS"].data.field("E_MIN")
      channelsEmax            = cspec["EBOUNDS"].data.field("E_MAX")
      spectra                 = cspec[cspecExtName].data
      spectraStart            = spectra.field("TIME")
      spectraStop             = spectra.field("ENDTIME")
      spectraExposure         = spectra.field("EXPOSURE")
      
      timeIntervals           = TimeIntervalFitsFile(timeBinsFile)
      newPHA2                 = Spectra()
      
      for interval in timeIntervals.getIntervals():
        #Find all spectra between start and stop
        mask                  = (spectraStop >= interval.tstart) & (spectraStart <= interval.tstop)
        
        #Compute the weight for each interval: the weight will be 1 for intervals
        #completely contained between tstart and tstop, and < 1 for the first and
        #last interval. The weighted sum of the counts give the channel counts between
        #tstart and tstop, assuming that they are distributed uniformly within the
        #first and last bin
        weight                  = []
        for i in mask.nonzero()[0]:
          weight.append((min(interval.tstop,spectraStop[i])-max(interval.tstart,spectraStart[i]))/
                        (spectraStop[i]-spectraStart[i]))  
        weight                = numpy.array(weight)
        
        if( len(( (weight >= 1E-4) & (weight <= 1-1E-4) ).nonzero()[0])!=0):
          sys.stderr.write("\n\nWARNING: time interval %s-%s is not covered exactly by the provided CSPEC file. The resulting spectra might be not accurate.\n\n" %(interval.tstart,interval.tstop))
        print(weight)
        #Sum channel by channel all counts
        countsToSum           = spectra[mask].field("COUNTS")
        nChan                 = len(countsToSum[0,:])
        exposure              = numpy.sum(spectra[mask].field("EXPOSURE")*weight)
        thisSpectrum          = Spectrum(interval.tstart,interval.tstop,exposure,
                                         telescope=self.telescope,instrument=self.instrument,poisserr=True,
                                         spectrumtype="TOTAL") 
        for chan in range(nChan):
          totalCounts         = numpy.sum(countsToSum[:,chan]*weight)
          error               = numpy.sqrt(totalCounts)
          thisSpectrum.addChannel(chan,channelsEmin[chan],channelsEmax[chan],totalCounts/exposure,error/exposure)
        pass
                 
        newPHA2.addSpectrum(thisSpectrum)
      pass
      newPHA2.write(outfile,format="PHA2",clobber=True)
      
      #Now add EBOUNDS and GTI to the new file
      ebounds                 = cspec["EBOUNDS"].copy()
      gti                     = cspec["GTI"].copy()
      f                       = pyfits.open(outfile)
      primary                 = f[0].copy()
      spectrum                = f['SPECTRUM'].copy()
      f.close()
      cspec.close()
      
      hdulist                 = pyfits.HDUList([primary,spectrum,ebounds,gti])
      hdulist.writeto("temp.pha__")
      os.remove(outfile)
      os.rename("temp.pha__",outfile)     
    pass
pass

class multiprocessScienceTools(dict):
  def __init__(self,scienceTool):
    #If there is more than one processor, use the multi-processor
    #version, otherwise the standard one
    configuration                      = Configuration()
    self.ncpus                         = min(int(float(configuration.get('maxNumberOfCPUs'))),multiprocessing.cpu_count()) #Save 1 processor for system usage
    if(self.ncpus > 1):
      self.run                         = self.multiproc_run
    else:
      self.run                         = self.singleproc_run
    pass
    self.scienceTool                   = scienceTool
    dict.__init__(self)
  pass
  
  def multiproc_run(self):
    #Virtual method
    pass
  pass
  
  def singleproc_run(self):
    tool                               = GtApp(self.scienceTool)
    for k,v in self.iteritems():
      tool[k]                      = v
    pass
    tool.run()
  pass
pass

class my_gtltcube(multiprocessScienceTools):
  def __init__(self):
    multiprocessScienceTools.__init__(self,'gtltcube')
  pass
  
  def multiproc_run(self):
    #return self.singleproc_run()
    
    #Get the length of the time interval
    data                               = pyfits.getdata(self['evfile'],'EVENTS')
    if(data.shape[0]==0 or (data.field("TIME").max()-data.field("TIME").min() <= 1000.0)):
      #Use the single processor version (there is no gain in splitting)
      return self.singleproc_run()
    else:
      pass
    
    exepath                            = os.path.join(os.path.dirname(__file__),'gtapps_mp','gtltcube_mp.py')
    cmdline                            = "%s %s %s %s %s" % (exepath,self.ncpus,
                                                                         self['scfile'],
                                                                         self['evfile'],
                                                                         self['outfile'])
    print cmdline
    process                            = subprocess.Popen(cmdline.split(), 
                                                          shell=False, stdout=subprocess.PIPE, 
                                                          stderr=subprocess.STDOUT)

    while True:
        out                            = process.stdout.readline()
        if out == '' and process.poll() is not None:
            break
        print out
    #gtltcube_mp(self.ncpus,
    #            self['scfile'],
    #            self['evfile'],
    #            self['outfile'], False, 180)
    print("\n")
  pass
pass

class my_gtdiffrsp(multiprocessScienceTools):
  def __init__(self):
    multiprocessScienceTools.__init__(self,'gtdiffrsp')
  pass
  
  def multiproc_run(self):
    #At the moment gtdiffrsp_mp is not very reliable (it fails sometimes),
    #so let's force the use of the single processor version
    return self.singleproc_run()
    exepath                            = os.path.join(os.path.dirname(__file__),'gtapps_mp','gtdiffrsp_mp.py')
    cmdline                            = "%s %s %s %s %s %s __gtdiffrsp_result.fits" % (exepath,self.ncpus,
                                                                         self['evfile'],
                                                                         self['scfile'],
                                                                         self['srcmdl'],
                                                                         self['irfs'])
    print cmdline
    process                            = subprocess.Popen(cmdline.split(), 
                                                          shell=False, stdout=subprocess.PIPE, 
                                                          stderr=subprocess.STDOUT)

    while True:
        out                            = process.stdout.readline()
        if out == '' and process.poll() is not None:
            break
        print out
    #gtdiffrsp_mp(self.ncpus, self['scfile'], self['evfile'], '__gtdiffrsp_result.fits', False, self['srcmdl'], self['irfs'])
    print("\n")
    shutil.copyfile("__gtdiffrsp_result.fits","%s" %(self['evfile']))
    os.remove("__gtdiffrsp_result.fits")
  pass
pass

class my_gttsmap(multiprocessScienceTools):
  def __init__(self):
    multiprocessScienceTools.__init__(self,'gttsmap')
  pass
  
  def multiproc_run(self):
    pars = {}

    pars['evfile']            = self['evfile']
    pars['scfile']            = self['scfile']
    pars['nxpix']             = self['nxpix']
    pars['nypix']             = self['nypix']
    pars['binsz']             = self['binsz']
    pars['coordsys']          = self['coordsys']
    pars['xref']              = self['xref']
    pars['yref']              = self['yref']
    pars['proj']              = self['proj']
    pars['expmap']            = self['expmap']
    pars['expcube']           = self['expcube']
    pars['srcmdl']            = self['srcmdl']
    pars['outfile']           = self['outfile']
    pars['irfs']              = self['irfs']
    pars['optimizer']         = self['optimizer']
    pars['ftol']              = self['ftol']
    pars['toltype']           = 1
    pars['jobs']              = self.ncpus
    exepath                            = os.path.join(os.path.dirname(__file__),'gtapps_mp','gttsmap_mp.py')
    cmdline                            = exepath+" %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s" % tuple([pars[k] for k in 'nxpix nypix jobs evfile scfile expmap expcube srcmdl irfs optimizer ftol toltype binsz coordsys xref yref proj outfile'.split()])
    print cmdline
    process                            = subprocess.Popen(cmdline.split(), 
                                                          shell=False, stdout=subprocess.PIPE, 
                                                          stderr=subprocess.STDOUT)

    while True:
        out                            = process.stdout.readline()
        if out == '' and process.poll() is not None:
            break
        print out
    print("\n")
  pass
pass


class my_gtexpmap(multiprocessScienceTools):
  def __init__(self):
    multiprocessScienceTools.__init__(self,'gtexpmap')
  pass
  
  def multiproc_run(self):
    if(self['nlong'] % 4 !=0):
      raise ValueError("nlong MUST be divisible by 4")
    if(self['nlat'] % 4 !=0):
      raise ValueError("nlat MUST be divisible by 4")
    
    if(self.ncpus==2 or self.ncpus==3):
      xbins                            = 2
      ybins                            = 1
    elif(self.ncpus==4 or self.ncpus==5):
      xbins                            = 2
      ybins                            = 2
    elif(self.ncpus==6 or self.ncpus==7):
      xbins                            = 3
      if(self['nlat'] % xbins !=0):
        print("Fixing nlong to be a multiple of 3")
        nlong                          = int(self['nlong'])
        while(1==1):
          nlong                       += 1
          if(nlong % 3==0):
            break
          pass
        pass
        print("nlong is now %s" %(nlong+6))
        self['nlong']                  = nlong+6
      pass     
      ybins                            = 2
    elif(self.ncpus>=8 and self.ncpus< 16):
      xbins                            = 4
      ybins                            = 2
    elif(self.ncpus>=16):
      xbins                            = 4
      ybins                            = 4
    pass
    
    exepath                            = os.path.join(os.path.dirname(__file__),'gtapps_mp','gtexpmap_mp.py')
    cmdline                            = "%s %s %s %s %s %s %s %s %s %s %s %s" % (exepath,self['nlong'], self['nlat'], 
                                                   xbins, ybins, self['scfile'], self['evfile'], self['expcube'], 
                                                   self['irfs'], self['srcrad'], self['nenergies'], self['outfile'])
    print cmdline
    process                            = subprocess.Popen(cmdline.split(), 
                                                          shell=False, stdout=subprocess.PIPE, 
                                                          stderr=subprocess.STDOUT)

    while True:
        out                            = process.stdout.readline()
        if out == '' and process.poll() is not None:
            break
        print out
    print("\n")
  pass

class LATData(LLEData):
  def __init__(self,*kargs,**kwargs):
    LLEData.__init__(self,*kargs,**kwargs)
    self.gtmktime                      = GtApp('gtmktime')
    self.gtltcube                      = my_gtltcube()
    self.gtexpmap                      = my_gtexpmap()
    self.gtlike                        = GtApp('gtlike')
    self.gtdiffrsp                     = my_gtdiffrsp()
    self.gtexpcube2                    = GtApp('gtexpcube2')
    self.gtsrcmaps                     = GtApp('gtsrcmaps')
    self.gtmodel                       = GtApp('gtmodel')
    self.gtobssim                      = GtApp('gtobssim')
    self.gtfindsrc                     = GtApp('gtfindsrc')
    self.gttsmap                       = my_gttsmap()
    self.gtrspgen                      = GtApp('gtrspgen')
    self.gtbkg                         = GtApp('gtbkg')
    
  pass
  
  def performStandardCut(self,ra,dec,rad,irf,tstart,tstop,emin,emax,zenithCut,thetaCut=180.0,gtmktime=True,roicut=True,**kwargs):
      self.strategy                    = 'time'
      
      for key in kwargs.keys():
        if(key=="strategy"):
          self.strategy                = kwargs[key]
        pass
      pass
      
      #Get tstart and tstop always in MET
      tstart                           = float(tstart)+int(float(tstart) < 231292801.000)*self.trigTime
      tstop                            = float(tstop)+int(float(tstop) < 231292801.000)*self.trigTime
      ra                               = float(ra)
      dec                              = float(dec)
      emin                             = float(emin)
      emax                             = float(emax)
      
      
      #Check that the FT2 file covers the time interval requested
      f                                = pyfits.open(self.ft2File)
      ft2max                           = max(f['SC_DATA'].data.STOP)
      ft2min                           = min(f['SC_DATA'].data.START)
      f.close()
      ft2max                           = float(ft2max)+int(float(ft2max) < 231292801.000)*self.trigTime
      ft2min                           = float(ft2min)+int(float(ft2min) < 231292801.000)*self.trigTime

      
      if(ft2min >= float(tstart)):
        sys.stderr.write("\n\nWARNING: Spacecraft file (FT2 file) starts after the beginning of the requested interval. Your start time is now %s (MET %s).\n\n" %(ft2min-self.trigTime,ft2min))
        tstart                         = ft2min
        time.sleep(2)
      if(ft2max <= float(tstop)):
        sys.stderr.write("\n\nWARNING: Spacecraft file (FT2 file) stops before the end of the requested interval. Your stop time is now %s (MET %s).\n\n" % (ft2max-self.trigTime,ft2max))
        tstop                          = ft2max
        time.sleep(2)
      pass
      
      if(tstop <= tstart):
        raise GtBurstException(14,"tstop=%s <= tstart=%s: wrong input or no data coverage for this interval" %(tstop,tstart))
      
      if(not self.eventFile):
        raise RuntimeError("You cannot select by time if you don't provide a FT1 file.")
      
      if(gtmktime):
        self.gtmktime['scfile']          = self.ft2File
        if(self.strategy=="time"):
          filt                           = "(DATA_QUAL>0 || DATA_QUAL==-1) && LAT_CONFIG==1 && IN_SAA!=T && LIVETIME>0 && (ANGSEP(RA_ZENITH,DEC_ZENITH,%s,%s)<=(%s-%s))" %(ra,dec,zenithCut,rad)
          self.gtmktime['roicut']        = "no"
        elif(self.strategy=="events"):
          filt                           = "(DATA_QUAL>0 || DATA_QUAL==-1) && LAT_CONFIG==1 && IN_SAA!=T && LIVETIME>0"
          self.gtmktime['roicut']        = "no"
        else:
          raise RuntimeError("Strategy must be either 'time' or 'events'")
        
        if(thetaCut!=180.0):
          filt                          += " && (ANGSEP(RA_SCZ,DEC_SCZ,%s,%s)<=%s)" %(ra,dec,thetaCut)
        pass
        
        self.gtmktime['filter']          = filt
        self.gtmktime['evfile']          = self.originalEventFile
        outfilemk                        = "%s_mkt.fit" %(self.rootName)
        self.gtmktime['outfile']         = outfilemk
        self.gtmktime['apply_filter']    = 'yes'
        self.gtmktime['overwrite']       = 'no'
        self.gtmktime['header_obstimes'] = 'yes'
        self.gtmktime['tstart']          = float(tstart)
        self.gtmktime['tstop']           = float(tstop)
        self.gtmktime['clobber']         = 'yes'
        try:
          self.gtmktime.run()
        except:
          raise GtBurstException(22,"gtmktime failed. Likely your filter resulted in zero exposure.")
      else:
        outfilemk                      = self.originalEventFile
      
      #Get the reprocessing version
      f                                = pyfits.open(self.originalEventFile)
      reprocessingVersion              = str(f[0].header['PROC_VER']).replace(" ","")
      f.close()
      print("\nUsing %s data\n" %(reprocessingVersion))
      
      self.gtselect['infile']          = outfilemk
      if(roicut):
        self.gtselect['ra']            = ra
        self.gtselect['dec']           = dec
        self.gtselect['rad']           = rad
      else:
        self.gtselect['ra']            = 'INDEF'
        self.gtselect['dec']           = 'INDEF'
        self.gtselect['rad']           = 'INDEF'
      tmin                             = float(tstart)
      tmax                             = float(tstop)
      self.gtselect['tmin']            = tmin
      self.gtselect['tmax']            = tmax
      self.gtselect['emin']            = emin
      self.gtselect['emax']            = emax
      self.gtselect['zmax']            = zenithCut
      
      if(irf.lower() in IRFS.IRFS.keys() and IRFS.IRFS[irf].validateReprocessing(str(reprocessingVersion))):
        irf                            = IRFS.IRFS[irf]
      else:
        raise ValueError("Class %s not known or wrong class for this reprocessing version (%s)." %(irf,reprocessingVersion))
      pass
      
      self.gtselect['evclass']         = irf.evclass
      self.gtselect['evclsmin']        = 0
      self.gtselect['evclsmax']        = 1000
      self.gtselect['convtype']        = -1
      self.gtselect['clobber']         = "yes"
      outfileselect                    = "%s_filt.fit" %(self.rootName)
      self.gtselect['outfile']         = outfileselect
      try:
        self.gtselect.run()
      except:
        raise GtBurstException(23,"gtselect failed for unknown reason")
      
      #Now write a keyword which will be used by other methods to recover ra,dec,rad,emin,emax,zcut
      f                                = pyfits.open(outfileselect,'update')      
      
      f[0].header.set('_ROI_RA',"%8.4f" % float(ra))
      f[0].header.set('_ROI_DEC',"%8.4f" % float(dec))
      f[0].header.set('_ROI_RAD',"%8.4f" % float(rad))
      f[0].header.set('_TMIN',"%50.10f" % float(tmin))
      f[0].header.set('_TMAX',"%50.10f" % float(tmax))
      f[0].header.set('_EMIN',"%s" % float(emin))
      f[0].header.set('_EMAX',"%s" % float(emax))
      f[0].header.set('_ZMAX',"%12.5f" % float(zenithCut))
      f[0].header.set('_STRATEG',self.strategy)
      f[0].header.set('_IRF',"%s" % irf.name)
      f[0].header.set('_REPROC','%s' % reprocessingVersion)
      
      nEvents                          = len(f['EVENTS'].data.TIME)
      print("\nSelected %s events." %(nEvents))
      f.close()

      #Use the filtered event list as eventfile now
      self.eventFile                   = outfileselect
      
      return outfileselect, nEvents
  pass
  
  def getCuts(self):
      f                             = pyfits.open(self.eventFile)
      h                             = f[0].header
      self.ra                       = float(h['_ROI_RA'])
      self.dec                      = float(h['_ROI_DEC'])
      self.rad                      = float(h['_ROI_RAD'])
      self.tmin                     = float(h['_TMIN'])
      self.tmax                     = float(h['_TMAX'])
      self.emin                     = float(h['_EMIN'])
      self.emax                     = float(h['_EMAX'])
      self.zmax                     = float(h['_ZMAX'])
      self.strategy                 = str(h['_STRATEG'])
      self.irf                      = str(h['_IRF'])
      self.reprocessingVersion      = str(h['_REPROC'])
      f.close()
  pass
  
  def doSkyMap(self,outfile,binsz=0.2,fullsky=False):    
     
     self.getCuts()
     
     #Run gtbin and do the skymap
     self.gtbin['evfile']           = self.eventFile
     self.gtbin['scfile']           = self.ft2File
     self.gtbin['outfile']          = outfile
     self.gtbin['algorithm']        = 'CMAP'
     
     nxpix                          = int(2*float(self.rad)/float(binsz))
     nypix                          = nxpix
     if(fullsky):
       nxpix                        = 360.0/float(binsz)
       nypix                        = 180.0/float(binsz)
     
     self.gtbin['nxpix']            = nxpix
     self.gtbin['nypix']            = nypix
     self.gtbin['binsz']            = binsz
     self.gtbin['coordsys']         = 'CEL'
     self.gtbin['xref']             = self.ra
     self.gtbin['yref']             = self.dec
     self.gtbin['axisrot']          = 0
     self.gtbin['rafield']          = 'RA'
     self.gtbin['decfield']         = 'DEC'
     self.gtbin['proj']             = projection
     try:
       self.gtbin.run()
     except:
       raise GtBurstException(24,"gtbin failed for unknown reason while producing the sky map")
  pass
    
  def doSkyCube(self,nebins=10,binsz=0.2):
     self.getCuts()
     
     self.gtbin['evfile']           = self.eventFile
     self.gtbin['scfile']           = self.ft2File
     outfile                        = "%s_skycube.fit" %(self.rootName)
     self.gtbin['outfile']          = outfile
     self.gtbin['algorithm']        = 'CCUBE'
     
     nxpix                          = int(2*float(self.rad)/float(binsz))+10
     nypix                          = nxpix
     self.gtbin['nxpix']            = nxpix
     self.gtbin['nypix']            = nypix
     self.gtbin['binsz']            = binsz
     self.gtbin['coordsys']         = 'CEL'
     self.gtbin['xref']             = self.ra
     self.gtbin['yref']             = self.dec
     self.gtbin['axisrot']          = 0
     self.gtbin['rafield']          = 'RA'
     self.gtbin['decfield']         = 'DEC'
     self.gtbin['proj']             = projection
     self.gtbin['ebinalg']          = 'LOG'
     self.gtbin['emin']             = self.emin
     self.gtbin['emax']             = self.emax
     self.gtbin['enumbins']         = nebins
     try:
       self.gtbin.run()
     except:
       raise GtBurstException(25,"gtbin failed for unknown reason while producing the sky cube")
     
     self.skyCube                   = outfile
  pass
  
  def makeLivetimeCube(self):
     self.getCuts()
     
     #Cut the FT2 (otherwise gtltcube is SUPER slow)
     shutil.copy(self.ft2File,"__ft2temp.fits")
     f                                = pyfits.open("__ft2temp.fits","update")
     idx                              = (f['SC_DATA'].data.START > self.tmin-300) & (f['SC_DATA'].data.STOP < self.tmax+300)
     f['SC_DATA'].data                = f['SC_DATA'].data[idx]
     f['SC_DATA'].header.set("TSTART",self.tmin-300)
     f['SC_DATA'].header.set("TSTOP",self.tmax+300)
     f.close()

     
     self.gtltcube['evfile']        = self.eventFile
     self.gtltcube['scfile']        = "__ft2temp.fits"
     outfilecube                    = "%s_ltcube.fit" %(self.rootName)
     self.gtltcube['outfile']       = outfilecube
     self.gtltcube['dcostheta']     = 0.025
     self.gtltcube['binsz']         = 1
     self.gtltcube['phibins']       = 1
     self.gtltcube['clobber']       = 'yes'
     if(self.strategy=="events"):
       print("\n\nApplying the Zenith cut in the livetime cube. Hope you know what you are doing...")
       self.gtltcube['zmax']        = self.zmax
     else:
       self.gtltcube['zmax']        = 180
     
     try:
       self.gtltcube.run()
     except:
       raise GtBurstException(26,"gtltcube failed in an unexpected way")     
     self.livetimeCube              = outfilecube
     os.remove("__ft2temp.fits")
  pass
  
  def makeExposureMap(self,binsz=1.0):
     self.getCuts()
     
     self.gtexpmap['evfile']        = self.eventFile
     self.gtexpmap['scfile']        = self.ft2File
     self.gtexpmap['expcube']       = self.livetimeCube
     outfileexpo                    = "%s_expomap.fit" %(self.rootName)
     self.gtexpmap['outfile']       = outfileexpo
     self.gtexpmap['irfs']          = self.irf
     self.gtexpmap['srcrad']        = (2*self.rad)
     #Guarantee that this is divisible by 4
     self.gtexpmap['nlong']         = 4*int(math.ceil(4*self.rad/binsz/4.0))
     self.gtexpmap['nlat']          = 4*int(math.ceil(4*self.rad/binsz/4.0))
     self.gtexpmap['nenergies']     = 20
     self.gtexpmap['clobber']       = 'yes'
     try:
       self.gtexpmap.run()
     except:
       raise GtBurstException(27,"gtexpmap failed in an unexpected way")
     self.exposureMap               = outfileexpo
  pass
    
  def makeBinnedExposureMap(self,binsz=1.0):
  
     self.getCuts()
     
     self.gtexpcube2['infile']      = self.livetimeCube 
     self.gtexpcube2['cmap']        = 'none'   
     nxpix                          = int(3*float(self.rad)/float(binsz))
     nypix                          = nxpix
     self.gtexpcube2['nxpix']       = nxpix
     self.gtexpcube2['nypix']       = nypix
     self.gtexpcube2['binsz']       = binsz
     self.gtexpcube2['coordsys']    = 'CEL'
     self.gtexpcube2['xref']        = self.ra
     self.gtexpcube2['yref']        = self.dec
     self.gtexpcube2['axisrot']     = 0
     self.gtexpcube2['proj']        = projection
     self.gtexpcube2['emin']        = self.emin
     self.gtexpcube2['emax']        = self.emax
     self.gtexpcube2['enumbins']    = 10
     
     outfileexpo                    = "%s_binExpMap.fit" %(self.rootName)
     self.gtexpcube2['outfile']     = outfileexpo
     self.gtexpcube2['irfs']        = self.irf
     self.gtexpcube2['clobber']     = 'yes'
     #All other parameters will be taken from the livetime cube
     try:
       self.gtexpcube2.run()
     except:
       raise GtBurstException(28,"gtexpcube2 failed in an unexpected way")
       
     self.binnedExpoMap             = outfileexpo
  pass
  
  def makeSourceMaps(self,xml):
     self.gtsrcmaps['scfile']       = self.ft2File
     self.gtsrcmaps['expcube']      = self.livetimeCube
     self.gtsrcmaps['cmap']         = self.skyCube
     self.gtsrcmaps['srcmdl']       = xml
     self.gtsrcmaps['irfs']         = self.irf
     self.gtsrcmaps['bexpmap']      = self.binnedExpoMap
     outfilesrcmap                  = "%s_srcMap.fit" %(self.rootName)
     self.gtsrcmaps['outfile']      = outfilesrcmap
     self.gtsrcmaps['clobber']      = 'yes'
     self.gtsrcmaps['resample']     = 'no'
     self.gtsrcmaps['minbinsz']     = 1.0
     self.gtsrcmaps['psfcorr']      = 'no'
     self.gtsrcmaps['emapbnds']     = 'no'     
     try:
       self.gtsrcmaps.run()
     except:
       raise GtBurstException(29,"gtsrcmaps failed in an unexpected way")
     self.sourceMaps                = outfilesrcmap
  pass
  
  def makeModelSkyMap(self,xml):
     self.getCuts()
     if(not hasattr(self,'skyCube')):
       self.doSkyCube()
     if(not hasattr(self,'binnedExpoMap')):
       self.makeBinnedExposureMap()
     if(not hasattr(self,'sourceMaps')):
       self.makeSourceMaps(xml)
     
     self.gtmodel['srcmaps']        = self.sourceMaps
     self.gtmodel['srcmdl']         = xml
     outfilemodelmap                = "%s_modelMap.fit" %(self.rootName)
     self.gtmodel['outfile']        = outfilemodelmap
     self.gtmodel['irfs']           = self.irf
     self.gtmodel['expcube']        = self.livetimeCube
     self.gtmodel['bexpmap']        = self.binnedExpoMap
     self.gtmodel['clobber']        = 'yes'
     try:
       self.gtmodel.run()
     except:
       raise GtBurstException(201,"gtmodel failed in an unexpected way")
     
     return outfilemodelmap
  pass
  
  def makeDiffuseResponse(self,xmlmodel):
     self.getCuts()
     
     self.gtdiffrsp['evfile']       = self.eventFile
     self.gtdiffrsp['scfile']       = self.ft2File
     self.gtdiffrsp['srcmdl']       = xmlmodel
     self.gtdiffrsp['irfs']         = self.irf
     self.gtdiffrsp['clobber']      = 'yes'
     try:
       self.gtdiffrsp.run()
     except:
       raise GtBurstException(202,"gtdiffrsp failed in an unexpected way")
  pass
  
  def makeResponse(self,phafile,numbins,thetacut=65,dcostheta=0.025):
     self.getCuts()
     
     self.gtrspgen['respalg']       = 'PS'
     self.gtrspgen['specfile']      = phafile
     self.gtrspgen['scfile']        = self.ft2File
     outfile                        = "%s_spec_%5.3f_%5.3f.rsp" %(self.rootName,self.tmin-self.trigTime,self.tmax-self.trigTime)
     self.gtrspgen['outfile']       = outfile
     self.gtrspgen['irfs']          = self.irf
     self.gtrspgen['thetacut']      = thetacut
     self.gtrspgen['dcostheta']     = dcostheta
     self.gtrspgen['ebinalg']       = 'LOG'
     self.gtrspgen['emin']          = 30.0
     self.gtrspgen['emax']          = 200000.0
     self.gtrspgen['enumbins']      = numbins
     try:
       self.gtrspgen.run()
     except:
       raise GtBurstException(203,"gtrspgen failed in an unexpected way")
     
     return outfile
  pass
  
  def binByEnergy(self,numbins):
     self.getCuts()
     
     #Re-implementing this     
     self.gtbin['evfile']           = self.eventFile
     self.gtbin['scfile']           = self.ft2File
     outfile                        = "%s_spec_%5.3f_%5.3f.pha" %(self.rootName,self.tmin-self.trigTime,self.tmax-self.trigTime)
     self.gtbin['outfile']          = outfile
     self.gtbin['algorithm']        = 'PHA1'
     self.gtbin['ebinalg']          = 'LOG'
     self.gtbin['emin']             = self.emin
     self.gtbin['emax']             = self.emax
     self.gtbin['enumbins']         = numbins
     try:
       self.gtbin.run()
     except:
       raise GtBurstException(204,"gtbin failed in an unexpected way while making a PHA1 file")
       
     return outfile
  pass
  
  def makeBackgroundFile(self,phafile,xmlmodel):
     self.getCuts()
     
     self.gtbkg['phafile']          = phafile
     outfile                        = "%s_spec_%5.3f_%5.3f.bak" %(self.rootName,self.tmin-self.trigTime,self.tmax-self.trigTime)
     self.gtbkg['outfile']          = outfile
     self.gtbkg['scfile']           = self.ft2File
     self.gtbkg['expcube']          = self.livetimeCube
     self.gtbkg['expmap']           = self.exposureMap
     self.gtbkg['irfs']             = self.irf
     self.gtbkg['srcmdl']           = xmlmodel
     name                           = _getParamFromXML(xmlmodel,'OBJECT')
     self.gtbkg['target']           = name
     try:
       self.gtbkg.run()
     except:
       raise GtBurstException(205,"gtbkg failed in an unexpected way")
     return outfile
  pass
  
  def doSpectralFiles(self,xmlmodel,numbins=None):
     self.getCuts()
     
     if(numbins==None):
       #Make a PHA1 file
       #10 bins for each decade in energy
       ndecades                       = numpy.log10(self.emax)-numpy.log10(self.emin)
       numbins                        = int(numpy.ceil(ndecades*10.0))
     pass
     
     phafile                          = self.binByEnergy(numbins)
     rspfile                          = self.makeResponse(phafile,numbins)
     bakfile                          = self.makeBackgroundFile(phafile,xmlmodel)
     
     return phafile,rspfile,bakfile
  pass
  
  def makeTSmap(self,xmlmodel,sourceName,binsz=0.7,side=None,outfile=None,tsltcube=None,tsexpomap=None):
     self.getCuts()
     if(tsltcube==None or tsltcube==''):
       self.makeLivetimeCube()
     else:
       self.livetimeCube            = tsltcube
     
     if(tsexpomap==None or tsexpomap==''):
       self.makeExposureMap()
     else:
       self.exposureMap             = tsexpomap
     pass
     
     self.makeDiffuseResponse(xmlmodel)     
     self.gttsmap['irfs']           = self.irf
     self.gttsmap['expcube']        = self.livetimeCube
     #We have to produce a version of the xmlmodel without the source
     tempModel                      = "__temp__xml_tsmap.xml"
     removePointSource(xmlmodel,tempModel,sourceName)
     self.gttsmap['srcmdl']         = tempModel
     self.gttsmap['statistic']      = "UNBINNED"
     self.gttsmap['optimizer']      = optimizer
     self.gttsmap['ftol']           = 1e-10
     self.gttsmap['evfile']         = self.eventFile
     self.gttsmap['scfile']         = self.ft2File
     self.gttsmap['expmap']         = self.exposureMap
     if(outfile==None):
       outfile                      = "%s_tsmap.fit" %(self.rootName)
     self.gttsmap['outfile']        = outfile
     
     if(side==None):
       self.gttsmap['nxpix']          = int(math.ceil(2*float(self.rad)/float(binsz)))
       self.gttsmap['nypix']          = int(math.ceil(2*float(self.rad)/float(binsz)))
     else:
       self.gttsmap['nxpix']          = int(math.ceil((float(side)/float(binsz))))
       self.gttsmap['nypix']          = int(math.ceil((float(side)/float(binsz))))
     pass
     
     #Fake values to avoid errors (this is a bug in recent version of the Science Tools)
     #They must be file FITS, but they will not be used
     self.gttsmap['cmap']           = self.exposureMap
     self.gttsmap['bexpmap']        = self.exposureMap
     
     self.gttsmap['binsz']          = binsz
     self.gttsmap['coordsys']       = "CEL"
     self.gttsmap['xref']           = self.ra
     self.gttsmap['yref']           = self.dec
     self.gttsmap['proj']           = projection
     self.gttsmap['chatter']        = 2
     print("Running gttsmap...")
     try:
       #Suppress output from gttsmap, which is VERY verbose with many "Info in <Minuit2>" messages       
       #with suppress_output(True,True):
         self.gttsmap.run()
     except:
       raise GtBurstException(206,"gttsmap failed in an unexpected way")
     os.remove(tempModel)
     return outfile
  pass
  
  def doBinnedLikelihoodAnalysis(self,xmlmodel,tsmin=20,**kwargs):
     expomap                        = None
     ltcube                         = None
     for k,v in kwargs.iteritems():
       if(k=='expomap'):
         expomap                    = v
       elif(k=='ltcube'):
         ltcube                     = v
       pass
     pass
     self.getCuts()
     if(ltcube==None or ltcube==''):
       self.makeLivetimeCube()
     else:
       if(os.path.exists(ltcube)):
         self.livetimeCube            = ltcube
       else:
         raise ValueError("The provided livetime cube (%s) does not exist." %(ltcube))
     pass
     
     self.doSkyCube()
     
     if(expomap==None or expomap==''):
       self.makeBinnedExposureMap()
     else:
       if(os.path.exists(expomap)):
         self.binnedExpoMap         = expomap
       else:
         raise ValueError("The provided exposure map (%s) does not exist." %(expomap))
       
     pass
     
     self.makeSourceMaps(xmlmodel)
          
     print("Loading python Likelihood interface...")
     
     self.obs                       = BinnedAnalysis.BinnedObs(srcMaps=self.sourceMaps,
                                                  expCube=self.livetimeCube,
                                                  binnedExpMap=self.binnedExpoMap,
                                                  irfs=self.irf)
     self.like1                     = BinnedAnalysis.BinnedAnalysis(self.obs,xmlmodel,optimizer='NEWMINUIT')
     
     return self._doLikelihood(xmlmodel,tsmin)
  
  pass
  
  def doUnbinnedLikelihoodAnalysis(self,xmlmodel,tsmin=20,**kwargs):
     expomap                        = None
     ltcube                         = None
     dogtdiffrsp                    = True
     for k,v in kwargs.iteritems():
       if(k=='expomap'):
         expomap                    = v
       elif(k=='ltcube'):
         ltcube                     = v
       elif(k=='dogtdiffrsp'):
         dogtdiffrsp                = bool(v)
       pass
     pass
     self.getCuts()
     if(ltcube==None or ltcube==''):
       self.makeLivetimeCube()
     else:
       if(os.path.exists(ltcube)):
         self.livetimeCube            = ltcube
       else:
         raise ValueError("The provided livetime cube (%s) does not exist." %(ltcube))
     pass
     
     if(expomap==None or expomap==''):
       self.makeExposureMap()
     else:
       if(os.path.exists(expomap)):
         self.exposureMap             = expomap
       else:
         raise ValueError("The provided exposure map (%s) does not exist." %(expomap))
       
     pass
     
     if(dogtdiffrsp):
       self.makeDiffuseResponse(xmlmodel)
          
     print("Loading python Likelihood interface...")
     
     self.obs                       = UnbinnedAnalysis.UnbinnedObs(self.eventFile,self.ft2File,
                                                  expMap=self.exposureMap,
                                                  expCube=self.livetimeCube,irfs=self.irf)
     self.like1                     = UnbinnedAnalysis.UnbinnedAnalysis(self.obs,xmlmodel,optimizer='NEWMINUIT')
     
     return self._doLikelihood(xmlmodel,tsmin)
  pass
   
  def _doLikelihood(self,xmlmodel,tsmin):
     
     outfilelike                    = "%s_likeRes.xml" %(self.rootName)
     
     #Add a Gaussian prior for the isotropicTemplate component (it should be either the 
     #isotropic template for Source class or the BKGE)
     #Open the XML to read in the statistical and systematic errors
     #f                              = open(xmlmodel)
     
     tree                           = ET.parse(xmlmodel)
     _root                           = tree.getroot()
     sysErr                         = None
     statErr                        = None
     
     #Get Isotropic DOM
     iso                            = _root.findall("./source[@name='IsotropicTemplate']")
     
     if(len(iso)==0):
       
       #No isotropic template
       print("\nNo isotropic template found in the XML file!")
     
     else:
       
       iso                          = iso[0]
       
       ps                           = iso.findall("./spectrum/parameter")
       
       if(len(ps)==0):
       
         raise RuntimeError("Malformed XML file! The Isotropic template source has no parameters!")
       
       param                        = ps[0]
       
       if(param.get('free')=='0'):
         #Parameter is fixed, do not add prior (which would cause an error in minuit)
         print("Isotropic template is fixed, not using any prior on it.")
       
       else:
         
         sysErr                       = float(iso.get('sysErr'))
         statErr                      = float(iso.get('statErr'))
         
         total_error                  = numpy.sqrt(numpy.power(sysErr,2)+ numpy.power(statErr,2))
         
         if(total_error!=0):
           
           print("\nApplying a Gaussian prior with sigma %s on the normalization of the Isotropic Template" %(total_error))
           idx                        = self.like1.par_index("IsotropicTemplate","Normalization")
	   self.like1[idx].addGaussianPrior(1.0,total_error)
           print self.like1[idx].getPriorParams()
         
         pass
       
       pass
     pass
          
     #Find the name of the GRB
     
     grb_name                 = None
     for s in self.like1.sourceNames():
       if(s.find(_getParamFromXML(xmlmodel,"OBJECT"))==0):
         grb_name             = s
     pass
     
     if(grb_name!=None):
       try:
         phIndex_beforeFit        = self.like1[grb_name]['Spectrum'].getParam("Index").value()
       except:
         phIndex_beforeFit        = -2
              
     else:
       phIndex_beforeFit        = -2
     pass
     
     #like1.ftol                     = 1e-10
     print("\nLikelihood settings:\n")
     print(self.like1)
     print("\nPerforming likelihood fit...")
     try:
       logL                         = self.like1.fit(verbosity=1,covar=True)
     except:
       raise RuntimeError("Likelihood fit did not converged. Probably your model is too complex for your selection.")
       
     self.like1.writeXml(outfilelike)
     
     #Now add the errors for the isotropic template, which are removed by writeXml
     if(sysErr!=None and statErr != None):
       tree                        = ET.parse(outfilelike)
       root                        = tree.getroot()
       for source in root.findall('source'):
         if(source.get('name')=='IsotropicTemplate'):
           source.set('sysErr','%s' %(sysErr))
           source.set('statErr','%s' %(statErr))
           break
         pass
       pass
       tree.write(outfilelike)
     pass
     
     try:
       self.like1.plot()
     except:
       print("Could not produce likelihood plots")
     pass
     
     if(grb_name!=None):
       try:
         self.like1.plotSource(grb_name,'red')
       except:
         pass
     for s in self.like1.sourceNames():
       if(s.lower().find("earthlimb")>=0):
         try:
           self.like1.plotSource(s,'blue')
         except:
           pass
         pass
       pass
     pass
     
     try:
       self.like1.residualPlot.canvas.Print('%s_residuals.png' % (self.rootName))
       self.like1.spectralPlot.canvas.Print('%s_spectral.png' % (self.rootName))
     except:
       pass
     pass
     
     printer                        = LikelihoodComponent.LikelihoodResultsPrinter(self.like1,self.emin,self.emax)
     detectedSources                = printer.niceXMLprint(outfilelike,tsmin,phIndex_beforeFit)
     print("\nLog(likelihood) = %s" %(logL))
     
     self.logL                      = logL
     self.resultsStrings            = printer.resultsStrings
     
     return outfilelike, detectedSources
  pass
  
  def optimizeSourcePosition(self,xmlmodel,sourceName='GRB'):
    self.getCuts()
    
    #Create a temporary xml file, otherwise gtfindsrc will overwrite the original one
    tmpxml                      = "__temp__xmlmodel.xml"
    try:
      os.remove(tmpxml)
    except:
      pass
    shutil.copy(xmlmodel,tmpxml)
    
    self.gtfindsrc['evfile']        = self.eventFile
    self.gtfindsrc['scfile']        = self.ft2File
    outfile                         = "%s_findsrc.txt" %(self.rootName)
    self.gtfindsrc['outfile']       = outfile
    self.gtfindsrc['irfs']          = self.irf
    self.gtfindsrc['expcube']       = self.livetimeCube
    self.gtfindsrc['expmap']        = self.exposureMap
    self.gtfindsrc['srcmdl']        = tmpxml
    self.gtfindsrc['target']        = sourceName
    self.gtfindsrc['optimizer']     = 'NEWMINUIT'
    self.gtfindsrc['ftol']          = 1E-10
    self.gtfindsrc['reopt']         = 'yes'
    self.gtfindsrc['atol']          = 1E-3
    self.gtfindsrc['posacc']        = 1E-2
    self.gtfindsrc['chatter']       = 5
    self.gtfindsrc['clobber']       = 'yes'
    
    stdin, stdout                   = self.gtfindsrc.runWithOutput()
    ra,dec,err                      = None,None,None
    for line in stdout.readlines():
      if(line.find("Best fit position:")>=0):
        ra,dec                      = line.split(":")[1].replace(" ","").split(",")
      elif(line.find("Error circle radius:")>=0):
        err                         = line.split(":")[1].replace(" ","")
      pass
    pass
    if(ra==None or dec==None or err==None):
      raise GtBurstException(207,"gtfindsrc execution failed. Were the source detected in the likelihood step?")
    pass
    try:
      os.remove(tmpxml)
    except:
      pass
    return float(ra),float(dec),float(err)
  pass
  
pass

class Simulation(object):
  def __init__(self,ft2File,irf,trigTime):
    self.ft2File = ft2File
    self.irf     = irfs[irf]
    self.trigTime = float(trigTime)
    self.gtobssim=GtApp('gtobssim')
    pass

  # -------------------------------------------------- #  
  
  def doSimulation(self,infile,srclist, evroot,simtime,tstart,seed):
    print 'I am now ready to simulate a GRB!'
    os.environ['SIMDIR']='$PWD'
    self.gtobssim['infile']  = infile
    self.gtobssim['srclist'] = srclist
    self.gtobssim['scfile']  = self.ft2File
    self.gtobssim['evroot']  = evroot
    self.gtobssim['simtime'] = simtime
    self.gtobssim['tstart']  = float(tstart)+int(float(tstart) < 231292801.000)*self.trigTime
    self.gtobssim['irfs']    = self.irf
    self.gtobssim['use_ac']  = 'no'
    self.gtobssim['seed']    = seed
    self.gtobssim['maxrows'] = int(1e9)
    self.gtobssim.run()
    
    outfile                  = glob.glob("%s_events_*.fits" %(evroot))
    if(len(outfile)==0):
      #File not produced!
      raise RuntimeError("Your simulation did not produce any event (or crashed). Is the GRB inside the FOV?")
    
    #Now open the simulated file and assign the data class
    f                        = pyfits.open(outfile[0],'update')
    event_class              = f['EVENTS'].data.EVENT_CLASS
    simEvent_class           = simirfs[self.irf]
    for i in range(len(event_class)):
      event_class[i]         = simEvent_class
    f.close()
    
    outfile                  = outfile[0]
    idsfile                  = glob.glob("%s_srcIds.txt" %(evroot))[0]
    
    f                        = open(idsfile,'r')
    print("\n%10s %30s %20s %20s" %('Source ID','Source name','Sim. events','Detect. events'))
    for line in f.readlines():
      srcid, name, ngen, nobs = line.split()
      print("%10s %30s %20s %20s" %(srcid.strip(),name.strip(),ngen.strip(),nobs.strip()))
    pass
    print("")
    f.close()
    return outfile, idsfile
    pass
  # -------------------------------------------------- #  
  pass

class TimeInterval(object):
  def __init__(self,tstart,tstop,swap=False):
    self.tstart               = tstart
    self.tstop                = tstop
    if(self.tstop <= self.tstart):
      if(swap):
        self.tstart           = tstop
        self.tstop            = tstart
      else:  
        raise RuntimeError("Invalid time interval! TSTART must be before TSTOP and TSTOP-TSTART >0.")
  pass
  
  def getDuration(self):
    return self.tstop-self.tstart
  pass
  
  def reduceToIntersection(self,interval):
    if not self.overlapsWith(interval):
      self.tstart               = None
      self.tstop                = None
      return None
    self.tstart                 = max(self.tstart,interval.tstart)
    self.tstop                  = min(self.tstop,interval.tstop)
  pass
  
  def merge(self,interval):
    if(self.overlapsWith(interval)):
      self.tstart               = min(self.tstart,interval.tstart)
      self.tstop                = max(self.tstop,interval.tstop)
    else:
      raise RuntimeError("Could not merge non-overlapping intervals!")
  pass
      
  def overlapsWith(self,interval):
    if(interval.tstart==self.tstart or interval.tstop==self.tstop):
      return True
    if(interval.tstart > self.tstart and interval.tstart < self.tstop):
      return True
    if(interval.tstop > self.tstart and interval.tstop < self.tstop):
      return True
    if(interval.tstart < self.tstart and interval.tstop > self.tstop):
      return True  
    return False  
pass

class TimeIntervalFitsFile(object):
  def __init__(self,fitsfile,referenceTime=0):
    f                         = pyfits.open(fitsfile)
    tstarts                   = f['TIMEBINS'].data.field("START")
    tstops                    = f['TIMEBINS'].data.field("STOP")
    
    self.intervals            = []
    for t1,t2 in zip(tstarts,tstops):
      self.intervals.append(TimeInterval(t1-referenceTime,t2-referenceTime))
    pass
    self.referenceTime        = referenceTime
    f.close()
  pass
  
  def getIntervals(self):
    return self.intervals
  pass
  
  def __str__(self):        
    #This is call by the print() command
    #Print results
    output                    = "\n------------------------------------------------------------"
    output                   += '\n| {0:^10} | {1:^20} | {2:^20} |'.format("INTERV.#","START","STOP")
    output                   += "\n|-----------------------------------------------------------"
    for i,interval in enumerate(self.intervals):
      output                 += '\n| {0:<10d} | {1:20.5g} | {2:20.5g} |'.format(i+1,interval.tstart,interval.tstop)
    pass
    output                   += "\n------------------------------------------------------------"
    output                   += "\n(* Time expressed from reference time: %s)" %(self.referenceTime)
    return output
  pass
 
  
pass

class CspecBackground(object):
  def __init__(self,cspecFile,rspFile):
    #Check that the file exists
    if(not _fileExists(cspecFile)):
      raise IOError("File %s does not exist!" %(cspecFile))
    pass
    
    self.cspecFile            = _getAbsPath(cspecFile)
    
    if(not _fileExists(cspecFile)):
      raise IOError("File %s does not exist!" %(rspFile))
    pass
    self.rspFile              = _getAbsPath(rspFile)
        
    #Get informations
    self.__readHeader()
    
    #Get the channels for this detector
    self.__readChannels()
    
    self.gtbin                = GtApp('gtbin')
    self.gtselect             = GtApp('gtselect')
    self.gtbindef             = GtApp('gtbindef')    
  pass
  
  def __readChannels(self):
    f                         = pyfits.open(self.cspecFile)
    ebounds                   = f["EBOUNDS"].data
    
    chanNumbers               = ebounds.field("CHANNEL")
    emin                      = ebounds.field("E_MIN")
    emax                      = ebounds.field("E_MAX")
    self.channels             = []
    
    for number,eemin,eemax in zip(chanNumbers,emin,emax):
      self.channels.append(Channel(number,eemin,eemax))
    pass
    f.close()
  pass
  
  def _getOptionalKeyword(self,header,keyword,default='none'):
    try:
      return header[keyword]
    except:
      return default 
  pass
  
  def __readHeader(self):
    #Get informations from the header of the file,
    #and fill attributes of the class
    self.trigTime             = getTriggerTime(self.cspecFile)
    f                         = pyfits.open(self.cspecFile)
    
    #Read the header of the SPECTRUM extension
    spectrumHeader            = f["SPECTRUM"].header
    
    #Harvest mandatory keywords
    self.tstart               = spectrumHeader['TSTART']    
    self.tstop                = spectrumHeader['TSTOP']    
    self.telescop             = spectrumHeader['TELESCOP']
    self.instrume             = spectrumHeader['INSTRUME']   
    self.chanType             = spectrumHeader['CHANTYPE']
    
    f.close()
    
    #Get the channel offset from the rsp file
    f                         = pyfits.open(self.rspFile)
    eboundsHeader             = f["EBOUNDS"].header
    try:
      self.channelOffset      = eboundsHeader['TLMIN1']
    except:
      self.channelOffset      = 1
    pass
    
    f.close()
  pass
  
  def getBackgroudSpectrum(self,bkgTimeIntervals,srcTimeIntervals):
    
    #Transform bkgTimeIntervals and srcTimeIntervals in lists,
    #if they are not already (this allow the user to specify both a single
    #interval and a list of intervals)
    bkgTimeIntervals          = _getIterable(bkgTimeIntervals)
    srcTimeIntervals          = _getIterable(srcTimeIntervals)
    
    #Fit the background
    polynomials               = self.polynomialFit(bkgTimeIntervals)
    
    #Instanciate the container for the spectra
    spectraContainer          = Spectra()
    
    #Get the spectra and fill the container
    for interval in srcTimeIntervals:
      
      #Since the polynomial fit return the "true" background rate,
      #the exposure for the background spectrum is equal to the duration
      #of the interval (deadtime = 0)
      duration                = interval.getDuration()
      thisSpectrum            = Spectrum(interval.tstart,interval.tstop,duration,
                                         telescope=self.telescop,instrument=self.instrume,
                                         backfile='none',respfile='none',ancrfile='none',
                                         spectrumType="BKG", chanType=self.chanType,
                                         poisserr=False)
      
      for channel,polynomial in zip(self.channels,polynomials):
        
        rate                  = polynomial.integral(interval.tstart,interval.tstop)/duration
        stat_err              = polynomial.integralError(interval.tstart,interval.tstop)/duration
        sys_err               = BACK_SYS_ERROR
        quality               = 0 #Good
        
        thisSpectrum.addChannel(channel.chanNumber,channel.emin,channel.emax,
                                rate,stat_err,quality,sys_err)
      
      pass
      spectraContainer.addSpectrum(thisSpectrum)
    pass
    
    #Add the EBOUNDS extension, which is not required by the OGIP PHA standard
    #but it is required by Rmfit (if it will ever support PHA 2 files...)
    f                         = pyfits.open(self.cspecFile)
    ebounds                   = f["EBOUNDS"]
    spectraContainer.addEboundsExtension(ebounds)
    f.close()
    
    return spectraContainer
    
  pass
  
  def polynomialFit(self,timeIntervals):
    #Transform timeIntervals in a list,
    #if it is not already (this allow the user to specify both a single
    #interval and a list of intervals)
    timeIntervals             = _getIterable(timeIntervals)
    self.timeIntervals        = timeIntervals
    
    cspec                     = pyfits.open(self.cspecFile)
    data                      = cspec["SPECTRUM"].data
    time                      = data.field("TIME")-self.trigTime
    endtime                   = data.field("ENDTIME")-self.trigTime
    
    #Select data to keep for the fit
    mask                      = None
    for interval in timeIntervals:
      thisMask                = (time >= interval.tstart) & (endtime <= interval.tstop)
      if(mask==None):
        mask                  = thisMask
      else:
        mask                  = (mask | thisMask)  
    pass
    filteredData              = data[mask]
    
    if(len(filteredData)==0):
      raise ValueError("The provided time intervals for the background fit resulted in no selected data. Cannot fit.")
    
    #Fit the sum of counts to get the optimal polynomial grade
    optimalPolGrade           = self._fitGlobalAndDetermineOptimumGrade(filteredData)
    
    #Compute the number of channels
    nChannels                 = len(filteredData.field("COUNTS")[0])
    polynomials               = []
    for chanNumber in range(nChannels):
      print("\nChannel %s: "%(chanNumber))
      thisPolynomial,cstat    = self._fitChannel(chanNumber,filteredData,optimalPolGrade)      
      print(thisPolynomial)
      print '{0:>20} {1:>6.2f} for {2:<5} d.o.f.'.format("logLikelihood = ",cstat,len(filteredData)-optimalPolGrade)
      polynomials.append(thisPolynomial)
    pass
    self.polynomials          = polynomials
    return polynomials
    
  pass
  
  def makeLightCurveWithResiduals(self,**kwargs):
    print("\nComputing residuals...\n")
    lcFigure                    = None
    for key in kwargs.keys():
      if    key.lower()=="figure":    
        lcFigure              = kwargs[key]
    pass  
    from matplotlib import pyplot as plt
    #Create figure
    if(lcFigure==None):
      lcFigure                = plt.figure()
      lcFigure.subplots_adjust(left=0.15, right=0.85, top=0.95, bottom=0.1)
      lcFigure.subplots_adjust(hspace=0)
    else:
      lcFigure.clear()
      lcFigure.canvas.draw()
    
    xlabel                      = "Time since trigger"
    ylabel                      = "Counts"
    subfigures                  = []
    trigTime                    = getTriggerTime(self.cspecFile)
    f                           = pyfits.open(self.cspecFile)  
    s                           = f['SPECTRUM']
    
    tstart                      = self.timeIntervals[0].tstart + self.trigTime
    tstop                       = self.timeIntervals[-1].tstop + self.trigTime
    mask                        = (s.data.field('QUALITY')==0) & (s.data.field("TIME") >= tstart) & (s.data.field("TIME")<= tstop) & (s.data.field("EXPOSURE")>0)
    d                           = s.data[mask]
    counts                      = d.field('COUNTS')
    t                           = d.field('TIME')-self.trigTime
    exposure                    = d.field('EXPOSURE')
    N                           = len(t)
    LC                          = N*[0]
    for j in range(N): 
      LC[j]                     = counts[j].sum()
    f.close()
    
    subfigures.append(lcFigure.add_subplot(2,1,1,xlabel=xlabel,ylabel=ylabel))           
    subfigures[-1].step(t,map(lambda x:x[0]/x[1],zip(LC,exposure)),where='post')
    subfigures[-1].xaxis.set_visible(False)
    #Now add the residuals
    residuals                   = []
    for i,t1,t2 in zip(range(N),t[:-1],t[1:]):
      backgroundCounts,backErr  = self.getTotalBackgroundCounts(t1,t2)
      liveFrac                  = exposure[i]/(t2-t1)
      try:
        residuals.append((LC[i]-backgroundCounts*liveFrac)/math.sqrt(backgroundCounts*liveFrac+pow(backErr*liveFrac,2.0))) 
      except:
        residuals.append(0)
    pass
    subfigures.append(lcFigure.add_subplot(2,1,2,xlabel=xlabel,ylabel="Sigma"))
    tmean                    = map(lambda x:(x[0]+x[1])/2.0,zip(t[:-1],t[1:]))
    subfigures[-1].errorbar(tmean,residuals,yerr=map(lambda x:1,tmean))
    subfigures[-1].set_ylim([min(residuals),min(max(residuals),10)])
    subfigures[-1].step(tmean,map(lambda x:0,tmean),"r--",where='post')
    
    #Wait for the window to close
    self.retryButton          = lcFigure.text(0.9, 0.15,'Retry',
                                     horizontalalignment='left', 
                                     verticalalignment='top',
                                     backgroundcolor='red',
                                     color='white',weight='bold',
                                     picker=5)
    self.acceptButton         = lcFigure.text(0.9, 0.05,'Ok',
                                     horizontalalignment='left', 
                                     verticalalignment='bottom',
                                     backgroundcolor='green',
                                     color='white',weight='bold',
                                     picker=5)
    self.cid                  = lcFigure.canvas.mpl_connect('pick_event', self.onPick)     
    lcFigure.canvas.draw()
    print("Done")
    self.lcFigure             = lcFigure
    self.lcFigure.canvas.start_event_loop(0)
  pass      
  
  def onPick(self,event):
    #If the user clicked on one of the texts, do the corresponding
    #action
    if(event.mouseevent.button!=1):
      #Do nothing
      return
    pass
    if(event.artist==self.retryButton):
      self.accepted           = False
    elif(event.artist==self.acceptButton):
      self.accepted           = True
    self.lcFigure.canvas.mpl_disconnect(self.cid)  
    self.lcFigure.canvas.stop_event_loop()
    self.lcFigure.clear()
    self.lcFigure.canvas.draw()
  pass
  
  def getTotalBackgroundCounts(self,t1,t2):
      totalCounts             = 0.0
      statError               = 0.0
      for channel,polynomial in zip(self.channels,self.polynomials):
        totalCounts          += polynomial.integral(t1,t2)
        statError            += pow(polynomial.integralError(t1,t2),2.0)
      pass
      statError               = math.sqrt(statError)
      return totalCounts, statError
  pass
  
  def _polyfit(self,x,y,exposure,polGrade):
    
    #Check that we have enough counts to perform the fit, otherwise
    #return a "zero polynomial"
    nonzeroMask               = ( y > 0 )
    Nnonzero                  = len(nonzeroMask.nonzero()[0])
    if(Nnonzero==0):
      #No data, nothing to do!
      return Polynomial([0.0]), 0.0
    pass  
    
    #Compute an initial guess for the polynomial parameters,
    #with a least-square fit (with weight=1) using SVD (extremely robust):
    #(note that polyfit returns the coefficient starting from the maximum grade,
    #thus we need to reverse the order)
    if(test):
      print("  Initial estimate with SVD..."),
    with warnings.catch_warnings():
      warnings.simplefilter("ignore")
      initialGuess            = numpy.polyfit(x,y/exposure,polGrade)
    pass
    initialGuess              = initialGuess[::-1]
    if(test):
      print("  done -> %s" %(initialGuess))
    
    
    polynomial                = Polynomial(initialGuess)
    
    #Check that the solution found is meaningful (i.e., definite positive 
    #in the interval of interest)
    M                         = polynomial(x)
    negativeMask              = (M < 0)
    if(len(negativeMask.nonzero()[0])>0):
      #Least square fit failed to converge to a meaningful solution
      #Reset the initialGuess to reasonable value
      initialGuess[0]         = numpy.mean(y)
      meanx                   = numpy.mean(x)
      initialGuess            = map(lambda x:abs(x[1])/pow(meanx,x[0]),enumerate(initialGuess))
    
    #Improve the solution using a logLikelihood statistic (Cash statistic)
    logLikelihood             = LogLikelihood(x,y,polynomial,exposure=exposure)        
    
    #Check that we have enough non-empty bins to fit this grade of polynomial,
    #otherwise lower the grade
    dof                       = Nnonzero-(polGrade+1)      
    if(test): 
      print("Effective dof: %s" %(dof))
    if(dof <= 2):
      #Fit is poorly or ill-conditioned, have to reduce the number of parameters
      while(dof < 2 and len(initialGuess)>1):
        initialGuess          = initialGuess[:-1]
        polynomial            = Polynomial(initialGuess)
        logLikelihood         = LogLikelihood(x,y,polynomial,exposure=exposure)  
      pass        
    pass

    #Try to improve the fit with the log-likelihood    
    #try:
    if(1==1):
      finalEstimate           = scipy.optimize.fmin(logLikelihood, initialGuess, 
                                                    ftol=1E-5, xtol=1E-5,
                                                    maxiter=1e6,maxfun=1E6,
                                                    disp=False)
    #except:
    else:
      #We shouldn't get here!
      raise RuntimeError("Fit failed! Try to reduce the degree of the polynomial.")
    pass
        
    #Get the value for cstat at the minimum
    minlogLikelihood          = logLikelihood(finalEstimate)
    
    #Update the polynomial with the fitted parameters,
    #and the relative covariance matrix
    finalPolynomial           = Polynomial(finalEstimate)
    try:
      finalPolynomial.computeCovarianceMatrix(logLikelihood.getFreeDerivs)             
    except Exception:
      raise
    #if test is defined, compare the results with those obtained with ROOT
    if(test):
      fitWithROOT(x,y,exposure,finalPolynomial)
    pass
    
    return finalPolynomial, minlogLikelihood
  pass
  
  def _fitGlobalAndDetermineOptimumGrade(self,data):
    #Fit the sum of all the channels to determine the optimal polynomial
    #grade
    Nintervals                = len(data)
    
    #Put data to fit in an x vector and y vector
    counts                    = data.field("COUNTS")
    x                         = numpy.array((data.field("TIME")+data.field("ENDTIME"))/2.0)
    x                        -= self.trigTime
    
    y                         = []
    for i in range(Nintervals):
      y.append(numpy.sum(counts[i]))
    pass
    y                         = numpy.array(y)
    
    exposure                  = numpy.array(data.field("EXPOSURE"))
    
    print("\nLooking for optimal polynomial grade:")
    #Fit all the polynomials
    minGrade                  = 0
    maxGrade                  = 4
    logLikelihoods            = []
    for grade in range(minGrade,maxGrade+1):      
      polynomial, logLike     = self._polyfit(x,y,exposure,grade)
      logLikelihoods.append(logLike)         
    pass
    #Found the best one
    deltaLoglike              = numpy.array(map(lambda x:2*(x[0]-x[1]),zip(logLikelihoods[:-1],logLikelihoods[1:])))
    print("\ndelta log-likelihoods:")
    for i in range(maxGrade):
      print("%s -> %s: delta Log-likelihood = %s" %(i,i+1,deltaLoglike[i]))
    pass
    print("") 
    deltaThreshold            = 9.0
    mask                      = (deltaLoglike >= deltaThreshold)
    if(len(mask.nonzero()[0])==0):
      #best grade is zero!
      bestGrade               = 0
    else:  
      bestGrade                 = mask.nonzero()[0][-1]+1
    pass
    
    if(test):
      fitWithROOT(x,y,exposure,prevPolynomial,True)
    pass
    
    return bestGrade
    
  pass
  
  def _fitChannel(self,chanNumber,data,polGrade):
        
    Nintervals                = len(data)
    
    #Put data to fit in an x vector and y vector
    counts                    = data.field("COUNTS")
    x                         = numpy.array((data.field("TIME")+data.field("ENDTIME"))/2.0)
    x                        -= self.trigTime
    
    y                         = []
    for i in range(Nintervals):
      y.append(counts[i][chanNumber])
    pass
    y                         = numpy.array(y)    
    
    exposure                  = numpy.array(data.field("EXPOSURE"))
    
    polynomial, minLogLike    = self._polyfit(x,y,exposure,polGrade)
    
    return polynomial, minLogLike
  pass
  
pass

class Channel(object):
  def __init__(self,chanNumber,emin,emax):
    self.chanNumber           = chanNumber
    self.emin                 = emin
    self.emax                 = emax
  pass  
pass

class Spectrum(object):
  '''
  Implements a single spectrum ("PHA type I")
  '''
  def __init__(self,tstart,tstop,exposure,**kwargs):
      
    self.tstart               = tstart
    self.tstop                = tstop
    self.exposure             = exposure
    
    #This dictionary will store the channels, having the chanNumber as
    #key and a Channel class as value
    self.channels             = {}
    
    #This channelOffset will be added to the channel numbers,
    #thus the first channel will be numbered channelOffset,
    #the second channelOffset+1 etc. Default: 1 (as Xspec expects)
    self.channelOffset        = 1
    
    #Response and background file (default = none)
    self.backfile             = 'none'
    self.respfile             = 'none'
    self.ancrfile             = 'none'
    
    #Set default values for the instrument
    self.telescope            = "UNKN-TELESCOPE"
    self.instrument           = "UNKN-INSTRUME"
    self.filter               = "UNKN-FILTER"
    
    #Default type for the spectrum (can be BKG, TOTAL or NET)
    self.spectrumType         = "BKG"
    
    #Default channel type is PHA (can be PHA or PI)
    self.chanType             = "PHA"
    
    #Default value for poisserr (False). Set to True to use Poisson error and
    #ignore the stat_err and sys_err column
    self.poisserr             = False
    
    #Update default values with keywords content, if specified
    for key in kwargs.keys():
      if  (key.lower()=="telescope"):          self.telescope    = kwargs[key]
      elif(key.lower()=="instrument"):         self.instrument   = kwargs[key]
      elif(key.lower()=="filter"):             self.filter       = kwargs[key]
      elif(key.lower()=="backfile"):           self.backfile     = kwargs[key]
      elif(key.lower()=="respfile"):           self.respfile     = kwargs[key]
      elif(key.lower()=="ancrfile"):           self.ancrfile     = kwargs[key]
      elif(key.lower()=="spectrumtype"):       self.spectrumType = kwargs[key]
      elif(key.lower()=="chantype"):           self.chanType     = kwargs[key]
      elif(key.lower()=="poisserr"):           self.poisserr     = kwargs[key]
    pass
    
    #The following dictionary will have channels as keys, and 
    #counts as values
    self.spectrum             = {}
    self.sortedChannelNumbers = []   
  pass
  
  def addChannel(self,chanNumber,emin,emax,rate,stat_err,quality=0,sys_err=0,grouping=1):
    '''     
     Add a channel to the spectrum. Parameters:
     
     chanNumber               Channel number (remember to be consistent with the response file!)
     emin                     Lower energy bound for this channel
     emax                     Upper energy bound for this channel
     rate                     Count rate (in counts/s)
     stat_err                 Statistical error for the rate
     quality                  Quality flag: 0=good,1=flagged bad by software,
                              2=flagged dubious by software,3,4=not used,
                              5=flagged bad by the user (default=0)
     sys_err                  Fractional systematic error (default=0)                         
     grouping                 Grouping flag (default=0)
     
     See http://heasarc.gsfc.nasa.gov/docs/heasarc/ofwg/docs/spectra/ogip_92_007/node7.html .                                            
    '''
    
    thisChannel               = Channel(chanNumber,emin,emax)
    
    #Store thisChannel as value of the channels dictionary (so we can retrieve it by 
    #using the chanNumber), and as key of the spectrum dictionary
    #Note: both the first and the second dictionary here will store just a
    #reference to the class thisChannel, thus using it twice does not mean it will
    #be stored twice.
    #It seems to be an unnecessary complication, but it will avoid duplicated channels
    #and it allow to insert channels out of order
    self.channels[chanNumber] = thisChannel
    self.spectrum[thisChannel]= (rate, stat_err, sys_err, quality, grouping)
    self.sortedChanellNumbers = sorted(self.channels.keys())
  pass 
  
  def getRates(self):
    return map(lambda key:self.spectrum[self.channels[key]][0],self.sortedChanellNumbers)
  pass
  
  def getStat_err(self):
    return map(lambda key:self.spectrum[self.channels[key]][1],self.sortedChanellNumbers)
  pass
  
  def getSys_err(self):
    return map(lambda key:self.spectrum[self.channels[key]][2],self.sortedChanellNumbers)
  pass
  
  def getQuality(self):
    return map(lambda key:self.spectrum[self.channels[key]][3],self.sortedChanellNumbers)
  pass
  
  def getGrouping(self):
    return map(lambda key:self.spectrum[self.channels[key]][4],self.sortedChanellNumbers)
  pass
  
  def writePHA1(self):
    #We don't need to implement this for the moment
    pass
  pass  
  
pass

class Spectra(object):
  def __init__(self,*args):
    
    #If no argument is passed, use default constructor,
    #otherwise construct the class starting from a PHA2 file
    if(len(args)==0):
      self._normalConstructor()
    else:
      self._constructorFromPHA2(*args)  
  pass
  
  def _normalConstructor(self):
    #This list will contain all the instances of the class Spectrum
    self.spectra              = []
    
    #The following lists corresponds to the different columns in the PHA/CSPEC
    #formats, and they will be filled up by addSpectrum()
    self.tstart               = []
    self.tstop                = []
    self.channel              = []
    self.rate                 = []
    self.stat_err             = []
    self.sys_err              = []
    self.quality              = []
    self.grouping             = []
    self.exposure             = []
    self.backfile             = []
    self.respfile             = []
    self.ancrfile             = []
    
    #These two lists store the maximum length of the filenames for background
    #ancillary and response files, we will need them when writing the PHA2/CSPEC file
    self.maxlengthbackfile    = 0
    self.maxlengthrespfile    = 0
    self.maxlengthancrfile    = 0
    
    #This is to indicate if all the spectra have poisson errors
    self.poisser              = False
    
    #The EBOUNDS extension is not required by the PHA 2 standard,
    #but IT IS required in the CSPEC file for it to be readable by Rmfit.
    #It can be added before writing to file using the method addEboundsExtension()
    self.ebounds              = None
    
    #These dictionaries will contain user-supplied keyword for the
    #primary and SPECTRUM extension of PHAII and/or CSPEC files
    self.spectrumHeader       = {}
    self.primaryHeader        = {}
  pass  
  
  def _getColOrKeyword(self,data,header,name):
    try:
      q                       = numpy.array(data.field(name))
    except:
      q                       = numpy.array(map(lambda x:header[name],range(len(data))))
    pass
    
    return q  
  pass
  
  def _getRate(self,data):
    try:
      rate                    = data.field("RATE")
    except:
      counts                  = data.field("COUNTS")
      rate                    = numpy.array(map(lambda x:x[0]/x[1],zip(counts,(data.field("TELAPSE")))))
    pass
    return rate    
  pass
  
  def _getColOrKeywordOrZeros(self,data,header,channels,name,defaultValue=0):
    #This returns always a matrix len(data)*len(channels)
    try:
      q                       = self._getColOrKeyword(data,header,name)
      if(q.ndim==1):
        #q has one value for spectrum, while we need N values for each i-th spectrum, where
        #N is len(channel[i]). Copy the value to generate an array for each spectrum
        q                       = numpy.array(map(lambda x:numpy.zeros(len(x))+q,channels))
      pass  
    except:
      q                       = numpy.array(map(lambda x:numpy.zeros(len(x))+defaultValue,channels))
    pass 
    
    return q 
  pass 
  
  def _constructorFromPHA2(self,pha2file):
    if(not _fileExists(pha2file)):
      raise IOError("File %s do not exists!" %(pha2file))
    pass
    
    f                         = pyfits.open(pha2file)
    
    header                    = f["SPECTRUM"].header
    spectrumExtData           = f["SPECTRUM"].data
    eboundsExtData            = f["EBOUNDS"].data
    emin                      = eboundsExtData.field("E_MIN")
    emax                      = eboundsExtData.field("E_MAX")
    channels                  = eboundsExtData.field("CHANNEL")
    ebounds                   = {}
    for i in range(len(eboundsExtData)):
      ebounds[channels[i]]    = Channel(channels[i],emin[i],emax[i])
    pass
    
    Nspectra                  = len(spectrumExtData)
    
    #Get some infos from the header
    telescope                 = header["TELESCOP"]
    instrument                = header["INSTRUME"]
    spectrumType              = header["HDUCLAS2"]
    chanType                  = header["CHANTYPE"]
    try:
      poisserr                = header["POISSERR"]
    except:
      poisserr                = True
    pass
          
    tstarts                   = spectrumExtData.field("TSTART")
    telapses                  = spectrumExtData.field("TELAPSE")
    tstops                    = tstarts+telapses    
    exposures                 = spectrumExtData.field("EXPOSURE")
    channels                  = spectrumExtData.field("CHANNEL")
    rates                     = self._getRate(spectrumExtData) 
    
    if(poisserr==True):
      stat_err                = None
    else:
      stat_err                = spectrumExtData.field("STAT_ERR")
    pass
    
    sys_err                   = self._getColOrKeywordOrZeros(spectrumExtData,header,channels,"SYS_ERR")
    quality                   = self._getColOrKeywordOrZeros(spectrumExtData,header,channels,"QUALITY")
    grouping                  = self._getColOrKeywordOrZeros(spectrumExtData,header,channels,"GROUPING")
    
    #Fix the grouping column (if all the grouping value for a given spectrum are 1, then subsitute the
    #array of 1s with just one 
    for i,group in enumerate(grouping):
      mask                    = (group==0)
      if(len(mask.nonzero()[0])==len(group)):
        grouping[i]           = 0
      pass
    pass
    
    backfiles                 = self._getColOrKeyword(spectrumExtData,header,"BACKFILE")
    respfiles                 = self._getColOrKeyword(spectrumExtData,header,"RESPFILE")
    ancrfiles                 = self._getColOrKeyword(spectrumExtData,header,"ANCRFILE")     
    
    self._normalConstructor()
    
    #add all the spectra contained in this PHA2
    for i in range(Nspectra):      
      thisSpectrum            = Spectrum(tstarts[i],tstops[i],exposures[i],
                                         telescope=telescope,instrument=instrument,
                                         backfile=backfiles[i],respfile=respfiles[i],ancrfile=ancrfiles[i],
                                         spectrumType=spectrumType, chanType=chanType,
                                         poisserr=poisserr)
      for j,chan in enumerate(channels[i]):
        if(stat_err!=None):
          thisStatErr         = stat_err[i][j]
          thisSysErr          = sys_err[i][j]
        else:
          thisStatErr         = None
          thisSysErr          = None
        pass
            
        thisSpectrum.addChannel(chan,ebounds[chan].emin,ebounds[chan].emax,
                                rates[i][j],thisStatErr,quality[i][j],thisSysErr,grouping[i][j])
      pass
                                  
      self.addSpectrum(thisSpectrum)
    pass
        
    #Now load the EBOUNDS extension, if any
    try:
      self.addEboundsExtension(f["EBOUNDS"])
    except:
      pass
    
    self.setPoisson()
    
    f.close()
  pass
  
  def setPoisson(self,value=None):
    '''
    Set the Poisson flag to True or to False. If used without arguments,
    take the value of the flag from the first loaded spectrum.
    '''
    if(value==None):
      #Use the value for the first spectrum
      self.poisserr            = self.spectra[0].poisserr
    else:
      self.poisserr            = bool(value)
    pass    
  pass
  
  def addSpectrum(self,spectrum):
    self.spectra.append(spectrum)
    
    #Fill all the lists
    self.tstart.append(spectrum.tstart)
    self.tstop.append(spectrum.tstop)
    self.channel.append(spectrum.channels.keys())
    self.rate.append(spectrum.getRates())
    self.stat_err.append(spectrum.getStat_err())
    self.sys_err.append(spectrum.getSys_err())
    self.quality.append(spectrum.getQuality())
    self.grouping.append(spectrum.getGrouping())
    self.exposure.append(spectrum.exposure)
    self.backfile.append(spectrum.backfile)
    self.respfile.append(spectrum.respfile)
    self.ancrfile.append(spectrum.ancrfile)
    
    #This is to store the maximum length of the strings describing background,
    #response and ancillary files, which is needed to write the columns in the correct
    #FITS format
    self.maxlengthbackfile    = max(map(lambda x:len(x),self.backfile))
    self.maxlengthrespfile    = max(map(lambda x:len(x),self.respfile))
    self.maxlengthancrfile    = max(map(lambda x:len(x),self.ancrfile))
    
    self.setPoisson()
  pass
  
  def addEboundsExtension(self,ebounds):
    self.ebounds              = ebounds.copy()
  pass
  
  def addKeywordtoSpectrum(self,keyword,value):
    self.spectrumHeader[keyword] = value
  pass
  
  def addKeywordtoPrimary(self,keyword,value):
    self.primaryHeader[keyword]  = value
  pass
    
  def write(self,filename,**kwargs):
    
    '''
      Write an OGIP-compliant PHA Type II (format=PHA2) file or a CSPEC (format=CSPEC) file.
    '''
    
    format                    = 'PHA2'
    clobber                   = False
    for key in kwargs.keys():
      if  (key.lower()=="format"):          
        format          = kwargs[key].upper()
        if(format!="PHA2" and format!="CSPEC"):
          raise ValueError("Could not recognize requested format in keyword 'format'. Allowed values are CSPEC and PHA2")
        pass
      elif(key.lower()=="clobber") :            clobber       = bool(kwargs[key])         
    pass
    
    if(_fileExists(filename) and clobber==False):
      raise IOError("Filename %s already exists and clobber is False. Cannot continue." %(filename))
    pass
    
    if(format=="PHA2"):
      self._writePHA2(filename,**kwargs)
    elif(format=="CSPEC"):
      self._writeCSPEC(filename,**kwargs)
    pass
  pass
  
  def _writePHA2(self,filename,**kwargs):
    
    trigTime                  = None
    clobber                   = False
    for key in kwargs.keys():
      if  (key.lower()=="trigtime"):            trigTime      = kwargs[key]
      elif(key.lower()=="clobber") :            clobber       = bool(kwargs[key])
    pass      
    
    Nchan          = len(self.rate[0])
    vectFormatD    = "%sD" %(Nchan)
    vectFormatI    = "%sI" %(Nchan) 
    
    if(trigTime!=None):
      #use trigTime as reference for TSTART
      tstartCol      = pyfits.Column(name='TSTART',format='D',
                                   array=numpy.array(self.tstart),unit="s",bzero=trigTime)
    else:
      tstartCol      = pyfits.Column(name='TSTART',format='D',
                                   array=numpy.array(self.tstart),unit="s")
    pass
    
    telapseCol     = pyfits.Column(name='TELAPSE',format='D',
                                     array=(numpy.array(self.tstop)-numpy.array(self.tstart)),unit="s")
                               
    spec_numCol    = pyfits.Column(name='SPEC_NUM',format='I',
                                   array=range(1,len(self.spectra)+1))
    
    channelCol     = pyfits.Column(name='CHANNEL',format=vectFormatI,
                                   array=numpy.array(self.channel))
    
    ratesCol       = pyfits.Column(name='RATE',format=vectFormatD,
                                   array=numpy.array(self.rate),unit="Counts/s")
    
    if(self.poisserr==False):
      stat_errCol    = pyfits.Column(name='STAT_ERR',format=vectFormatD,
                                     array=numpy.array(self.stat_err))
    
      sys_errCol     = pyfits.Column(name='SYS_ERR',format=vectFormatD,
                                     array=numpy.array(self.sys_err))
    pass
    
    qualityCol     = pyfits.Column(name='QUALITY',format=vectFormatI,
                                   array=numpy.array(self.quality))
    
    groupingCol    = pyfits.Column(name='GROUPING',format=vectFormatI,
                                   array=numpy.array(self.grouping))
    
    exposureCol    = pyfits.Column(name='EXPOSURE',format='D',
                                   array=numpy.array(self.exposure),unit="s")
    
    backfileCol    = pyfits.Column(name='BACKFILE',format='%iA' %(self.maxlengthbackfile+2),
                                   array=numpy.array(self.backfile))
    
    respfileCol    = pyfits.Column(name='RESPFILE',format='%iA' %(self.maxlengthrespfile+2),
                                   array=numpy.array(self.respfile))                               
    
    ancrfileCol    = pyfits.Column(name='ANCRFILE',format='%iA' %(self.maxlengthancrfile+2),
                                   array=numpy.array(self.ancrfile))
    
    if(self.poisserr==False):                                                                                             
      coldefs        = pyfits.ColDefs([tstartCol,telapseCol,spec_numCol,channelCol,
                                       ratesCol,stat_errCol,sys_errCol,
                                       qualityCol,groupingCol, exposureCol,
                                       backfileCol,respfileCol,ancrfileCol])
    else:
      #If POISSERR=True there is no need for stat_err and sys_err
      coldefs        = pyfits.ColDefs([tstartCol,telapseCol,spec_numCol,channelCol,
                                       ratesCol,
                                       qualityCol,groupingCol, exposureCol,
                                       backfileCol,respfileCol,ancrfileCol])
    pass
    
    newTable       = pyfits.new_table(coldefs)
        
    #Add the keywords required by the OGIP standard:
    #Set POISSERR=F because our errors are NOT poissonian!
    #(anyway, neither Rmfit neither XSPEC actually uses the errors
    #on the background spectrum, BUT rmfit ignores channel with STAT_ERR=0)
    newTable.header.set('EXTNAME','SPECTRUM')
    newTable.header.set('CORRSCAL',1.0)
    newTable.header.set('AREASCAL',1.0)
    newTable.header.set('BACKSCAL',1.0) 
    newTable.header.set('HDUCLASS','OGIP')    
    newTable.header.set('HDUCLAS1','SPECTRUM')
    newTable.header.set('HDUCLAS2',self.spectra[0].spectrumType)
    newTable.header.set('HDUCLAS3','RATE')
    newTable.header.set('HDUCLAS4','TYPE:II')
    newTable.header.set('HDUVERS','1.2.0')
    newTable.header.set('TELESCOP',self.spectra[0].telescope)
    newTable.header.set('INSTRUME',self.spectra[0].instrument)
    
    if(self.spectra[0].filter!='unknown'):
      newTable.header.set('FILTER',self.spectra[0].filter)
    
    newTable.header.set('CHANTYPE',self.spectra[0].chanType)
    newTable.header.set('POISSERR',self.poisserr)
    newTable.header.set('DETCHANS',len(self.channel[0]))
    newTable.header.set('CREATOR',"dataHandling.py v.%s" %(moduleVersion),"(G.Vianello, giacomov@slac.stanford.edu)")
    
    for key,value in self.spectrumHeader.iteritems():
      newTable.header.set(key,value)
    pass
    
    #Write to the required filename
    newTable.writeto(filename,clobber=clobber)
    
    #Reopen the file and add the primary keywords, if any
    f                         = pyfits.open(filename,"update")
    for key,value in self.primaryHeader.iteritems():
      f[0].header.set(key,value)
    pass
    f.close()
    
    if(self.ebounds != None):
      pyfits.append(filename,self.ebounds.data,header=self.ebounds.header)
    pass
    
  pass  
  
  def _writeCSPEC(self,filename,**kwargs):
    
    if(self.ebounds==None):
      print("\n\nWARNING: no EBOUNDS loaded for the current Spectra. The produced CSPEC file will not be readable by Rmfit.")
      print("\n\n")
    pass
    
    #CSPEC file need a TRIGTIME keyword, if it is not provided use the beginning
    #of the first spectrum as default value
    trigTime                  = min(self.tstart)
    clobber                   = False
    for key in kwargs.keys():
      if  (key.lower()=="trigtime"):            trigTime      = kwargs[key]
      elif(key.lower()=="clobber") :            clobber       = bool(kwargs[key])
    pass
    
    Nchan          = len(self.rate[0])
    vectFormatD    = "%sD" %(Nchan)
    vectFormatI    = "%sJ" %(Nchan) 
    
    dt             = numpy.array(self.tstop)-numpy.array(self.tstart)
    
    counts         = map(lambda x:x[0]*x[1],zip(numpy.array(self.rate),dt))
    
    countsCol      = pyfits.Column(name='COUNTS',format=vectFormatI,
                                   array=numpy.array(counts),
                                   unit="Counts")
    if(self.poisserr==False):
      stat_err     = map(lambda x:x[0]*x[1],zip(numpy.array(self.stat_err),dt))
      stat_errCol  = pyfits.Column(name='STAT_ERR',format=vectFormatD,
                                     array=numpy.array(stat_err))
      sys_err      = map(lambda x:x[0]*x[1],zip(numpy.array(self.sys_err),dt))
      sys_errCol   = pyfits.Column(name='SYS_ERR',format=vectFormatD,
                                     array=numpy.array(sys_err))
    pass
    
    exposureCol    = pyfits.Column(name='EXPOSURE',format='D',
                                   array=numpy.array(self.exposure),unit="s")
                                   
    #If there is even just one bad channel in a given spectrum, set its quality as bad    
    qualityCol     = pyfits.Column(name='QUALITY',format="I",
                                   array=numpy.array(map(lambda x:max(x),self.quality)))
            
    timeCol        = pyfits.Column(name='TIME',format='D',
                                   array=numpy.array(self.tstart),unit="s",bzero=trigTime)
    
    endtimeCol     = pyfits.Column(name='ENDTIME',format='D',
                                     array=numpy.array(self.tstop),unit="s",bzero=trigTime)
    
    

    if(self.poisserr==False):                                                                                             
      coldefs      = pyfits.ColDefs([countsCol,stat_errCol,sys_errCol,
                                     exposureCol,qualityCol,timeCol,endtimeCol])
    else:
      #If POISSERR=True there is no need for stat_err and sys_err
      coldefs      = pyfits.ColDefs([countsCol,
                                     exposureCol,qualityCol,timeCol,endtimeCol])
    pass

    newTable       = pyfits.new_table(coldefs)
        
    #Add the keywords required by the OGIP standard:
    #Set POISSERR=F because our errors are NOT poissonian!
    #(anyway, neither Rmfit neither XSPEC actually uses the errors
    #on the background spectrum, BUT rmfit ignores channel with STAT_ERR=0)
    newTable.header.set('EXTNAME','SPECTRUM')
    newTable.header.set('CORRSCAL',1.0)
    newTable.header.set('AREASCAL',1.0)
    newTable.header.set('BACKSCAL',1.0) 
    newTable.header.set('HDUCLASS','OGIP')    
    newTable.header.set('HDUCLAS1','SPECTRUM')
    newTable.header.set('HDUCLAS2',self.spectra[0].spectrumType)
    newTable.header.set('HDUCLAS3','COUNT')
    newTable.header.set('HDUCLAS4','TYPE:II')
    newTable.header.set('HDUVERS','1.0.0')
    newTable.header.set('TELESCOP',self.spectra[0].telescope)
    newTable.header.set('INSTRUME',self.spectra[0].instrument)
    
    if(self.spectra[0].filter!='unknown'):
      newTable.header.set('FILTER',self.spectra[0].filter)
    
    newTable.header.set('CHANTYPE',self.spectra[0].chanType)
    newTable.header.set('POISSERR',self.poisserr)
    newTable.header.set('DETCHANS',len(self.channel[0]))
    newTable.header.set('TRIGTIME',trigTime)
    newTable.header.set('CREATOR',"dataHandling.py v.%s" %(moduleVersion),"(G.Vianello, giacomov@slac.stanford.edu)")
    
    for key,value in self.spectrumHeader.iteritems():
      newTable.header.set(key,value)
    pass
    
    #Write to the required filename
    
    #Primary EXT
    primaryExt                = pyfits.PrimaryHDU(numpy.array([]))

    #Add the keywords to identify the format
    self.primaryHeader["DATATYPE"] = 'CSPEC   '
    self.primaryHeader["FILETYPE"] = 'PHAII   '
    for key,value in self.primaryHeader.iteritems():
      primaryExt.header.set(key,value)
    pass
    
    if(self.ebounds != None):
      hduList                   = pyfits.HDUList([primaryExt,self.ebounds,newTable])
      #pyfits.append(filename,self.ebounds.data,header=self.ebounds.header)
    else:    
      hduList                   = pyfits.HDUList([primaryExt,newTable])
    pass
    
    hduList.writeto(filename,clobber=clobber)    
  pass
  
pass

def fixHeaders(llefile,cspecfile,sourceExt=eventsExtName,destExt="SPECTRUM"):
  '''
  Copy some keywords from the first file to the second file
  '''
  
  keywordsToCopyPrimary       = ["TELESCOP", "INSTRUME", "EQUINOX ", 
                                 "RADECSYS", "DATE    ", "DATE-OBS", 
                                 "DATE-END", "TIMEUNIT", "TIMEZERO", 
                                 "TIMESYS ", "TIMEREF ", "CLOCKAPP", 
                                 "GPS_OUT ", "MJDREFI ", "MJDREFF ", 
                                 "OBSERVER", "PASS_VER", "DATATYPE", 
                                 "RA_OBJ  ", "DEC_OBJ ", "OBJECT  ", 
                                 "TRIGTIME", "LONGSTRN", "LLECUT",
                                 "DETNAM"]
  
  keywordsToCopySpectrum      = ["TELESCOP", "INSTRUME", "EQUINOX ", 
                                 "RADECSYS", "DATE    ", "DATE-OBS", 
                                 "DATE-END", "OBSERVER", "MJDREFI ", 
                                 "MJDREFF ", "TIMEUNIT", "TIMEZERO", 
                                 "TIMESYS ", "TIMEREF ", "CLOCKAPP", 
                                 "GPS_OUT ", "PASS_VER", "RA_OBJ  ", 
                                 "DEC_OBJ ", "OBJECT  ", "LONGSTRN", 
                                 "LLECUT  ", "DETNAM"]
  
  if(_fileExists(llefile)==False):
    raise IOError("File %s does not exists!" %(llefile))
  pass
  llefile                     = _getAbsPath(llefile)
  
  if(_fileExists(cspecfile)==False):
    raise IOError("File %s does not exists!" %(cspecfile))
  pass
  cspecfile                   = _getAbsPath(cspecfile)
  
  #Copy from the TTE file some keywords
  llef                        = pyfits.open(llefile)
  llePrimary                  = llef[0].header
  lleSpectrum                 = llef[sourceExt].header
  
  cspecf                      = pyfits.open(cspecfile,"update")
  cspecPrimary                = cspecf[0].header
  cspecSpectrum               = cspecf[destExt].header
  
  for key in keywordsToCopyPrimary:
    try:
      value                     = llePrimary[key]
      comments                  = llePrimary.comments[key]
    except:
      continue
    pass
      
    cspecPrimary.set(key,value,comments)
  pass
  
  for key in keywordsToCopySpectrum:
    try:
      value                     = lleSpectrum[key]
      comments                  = lleSpectrum.comments[key]
    except:
      continue
    pass
      
    cspecSpectrum.set(key,value,comments)
  pass
  llef.close()
  cspecf.close()
pass

def findMaximumTSmap(tsmap,tsexpomap):
  #Find the maximum of the TS map
  f                           = pyfits.open(tsmap)
  image                       = f[0].data
  wcs                         = pywcs.WCS(f[0].header)
  f.close()
    
  #Position of the maximum
  idxs                        = numpy.unravel_index(image.argmax(), image.shape)
  #R.A., Dec of the maximum (the +1 is due to the FORTRAN Vs C convention
  ra,dec                      = wcs.wcs_pix2sky(idxs[1]+1,idxs[0]+1,1)
  ra,dec                      = ra[0],dec[0]
  
  #Now check that the value in the exposure map for this ra,dec is not too small,
  #nor that this Ra,Dec is at the margin of an excluded zones
  #(this avoid triggering on the Earth limb when strategy=events)
  fexp                        = pyfits.open(tsexpomap)
  expmap                      = fexp[0].data[0]
  wcsexp                      = pywcs.WCS(fexp[0].header)
  fexp.close()
  
  while(1==1):
    #Note that the value of one pixel is valid from .5 to 1.5
    #Note also that the exposure map is larger than the TS map
    pixels                    = wcsexp.wcs_sky2pix([[ra,dec,1]],1)[0]
    exposureHere              = expmap[pixels[1]-0.5,pixels[0]-0.5]
    exposureUp                = expmap[pixels[1]-0.5-1,pixels[0]-0.5]
    exposureDown              = expmap[pixels[1]-0.5+1,pixels[0]-0.5]
    exposureRight             = expmap[pixels[1]-0.5,pixels[0]-0.5-1]
    exposureLeft              = expmap[pixels[1]-0.5,pixels[0]-0.5+1]
    #print("Exposure: %s" %(exposureHere))
    if(exposureHere > 0 and 
       exposureUp > 0 and 
       exposureDown > 0 and 
       exposureLeft > 0 and 
       exposureRight > 0):
      break
    else:
      #Mask out this value
      print("Neglecting maximum at %s,%s because of low exposure there..." %(ra,dec))
      image[idxs[0],idxs[1]]  = 0.0
      idxs                        = numpy.unravel_index(image.argmax(), image.shape)
      #R.A., Dec of the maximum (the +1 is due to the FORTRAN Vs C convention
      ra,dec                      = wcs.wcs_pix2sky(idxs[1]+1,idxs[0]+1,1)
      ra,dec                      = ra[0],dec[0]
      continue
    pass
  pass
  
  tsmax                       = image.max()
  return ra,dec, tsmax
pass
