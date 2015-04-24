#This class imlements the 4 components relevant for the likelihood fit
#for GRBs

#FuncFactory is part of the Science Tools
import pywcs
from FuncFactory import *
import os
import xml.etree.ElementTree as ET
import math
from GtBurst.angularDistance import getAngularDistance
from GtBurst import bkge
import numpy
import os
from GtBurst.getDataPath import getDataPath
from GtBurst import IRFS
from GtBurst import GtBurstException
from GtBurst import cutout
import pyfits
import collections

#List of available spectra, and respective constructors
availableSourceSpectra        = IRFS.CaseInsensitiveDict()
#The order here is what will show up in the menu in the GUI,
#in particular the first model will become the pre-defined choice
availableSourceSpectra['PowerLaw2'] =  PowerLaw2
availableSourceSpectra['PowerLaw'] =  PowerLaw
availableSourceSpectra['ExpCutoff'] =  ExpCutoff
availableSourceSpectra['BPLExpCutoff'] =  BPLExpCutoff
availableSourceSpectra['BrokenPowerLaw'] =  BrokenPowerLaw
availableSourceSpectra['BrokenPowerLaw2'] =  BrokenPowerLaw2
availableSourceSpectra['LogParabola'] =  LogParabola
availableSourceSpectra['Gaussian'] =  Gaussian
availableSourceSpectra['PLSuperExpCutoff'] =  PLSuperExpCutoff


def findGalacticTemplate(irfname,ra,dec,rad):
  irf                         = IRFS.IRFS[irfname]
  
  templ                       = findTemplate(irf.galacticTemplate)
  if(templ==None):
    raise GtBurstException.GtBurstException(61,"You don't have a Galactic template for IRF %s. Cannot continue." %(irfname))
  else:
    print("\nFound Galactic template for IRF. %s: %s" %(irfname,templ))
    print("\nCutting the template around the ROI: \n")
    name,ext                  = os.path.basename(templ).split(".")
    newName                   = name+"_cut.%s" % ext
    cutout.cutout(templ,ra,dec,'equatorial',rad,newName,True)
    return os.path.abspath(os.path.join('.',newName))
pass

def findIsotropicTemplate(irfname):
  if(irfname=='BKGE'):
    templ                     = os.environ.get('THISBKGE') #This is a trick, leave it as it is
  else:
    irf                       = IRFS.IRFS[irfname]
    templ                     = findTemplate(irf.isotropicTemplate)
  pass
  
  if(templ==None):
    raise GtBurstException.GtBurstException(61,"You don't have an Isotropic template for IRF %s. Cannot continue." %(irfname))
  else:
    print("\nFound Isotropic template for irf %s: %s" %(irfname,templ))
    return templ
pass

def findTemplate(options):
  templates                   = options.replace(" ","").split(",")
  foundTemplate               = None
  envvar                      = os.environ.get("FERMI_DIR")
  publicTools                 = True
  if(envvar==None):
    #This is for versions of ST internal to the collaboration
    envvar                    = os.environ.get("GLAST_EXT")
    publicTools               = False
    if(envvar==None):
      raise RuntimeError("Fermi Science tools are not properly configured. No FERMI_DIR nor GLAST_EXT variables are set. Cannot continue.")
    pass
  pass
  
  if(os.environ.get('GTBURST_TEMPLATE_PATH')==None):
    #This is normally the case
    if(publicTools):
      path                        = os.path.abspath(os.path.expanduser(os.path.join(envvar,'refdata','fermi','galdiffuse')))
    else:
      if(os.environ.get('DIFFUSE_VER')==None):
        ver                       = 'v2r0'
      else:
        ver                       = os.environ.get('DIFFUSE_VER')
      pass
      
      path                        = os.path.abspath(os.path.expanduser(os.path.join(envvar,'diffuseModels',ver)))
    pass
  else:
    #The user forces the template path
    
    path                          = os.environ.get('GTBURST_TEMPLATE_PATH')
    print("\n\nUsing user-defined path for templates: %s\n\n" %(path))
  pass
  
  for tmp in templates:
    thisTrial                 = os.path.join(path,tmp)
    if(os.path.exists(thisTrial)):
      return thisTrial
    pass
  pass
  
  #If we are here no template has been found
  print("\nI was looking for %s into %s\n" %(",".join(templates), path))
  return None
pass

def DiffuseSrcTemplateFunc(irf,ra,dec,rad):
    diffuse = '''
   <spatialModel file="%s" type="MapCubeFunction">
     <parameter free="0" max="1000.0" min="0.001" name="Normalization" scale= "1.0" value="1.0"/>
   </spatialModel>
    ''' %(findGalacticTemplate(irf,ra,dec,rad))
    
    spectrum = '''
   <spectrum type="ConstantValue">
     <parameter free="1" max="10.0" min="0.0" name="Value" scale="1.0" value= "1.0"/>
   </spectrum>
    '''
    completeExpression        = '<source name="diffuse source template" type="DiffuseSource">%s\n%s\n</source>' %(diffuse,spectrum)
    (src, )                   = minidom.parseString(completeExpression).getElementsByTagName('source')
    src                       = Source(src)
    
    (spectrumXML,)            = minidom.parseString(spectrum).getElementsByTagName('spectrum')
    src.spectrum              = Function(spectrumXML)
    src.deleteChildElements('spectrum')
    src.node.appendChild(src.spectrum.node)
    
    (func,)                   = minidom.parseString(diffuse).getElementsByTagName('spatialModel')
    src.spatialModel          = Function(func)
    src.deleteChildElements('spatialModel')
    src.node.appendChild(src.spatialModel.node)

    return src
pass

def IsotropicTemplateFunc(irf):
    diffuse = '''
   <spatialModel type="ConstantValue">
      <parameter free="0" max="10.0" min="0.0" name="Value" scale="1.0" value="1.0"/>
   </spatialModel>
    '''
    
    spectrum = '''
   <spectrum file="%s" type="FileFunction">
      <parameter free="1" max="1000" min="1e-05" name="Normalization" scale="1" value="1" />
   </spectrum>
    ''' % (findIsotropicTemplate(irf))
    
    completeExpression        = '<source name="isotropic template" type="DiffuseSource">%s\n%s\n</source>' %(diffuse,spectrum)
    (src, )                   = minidom.parseString(completeExpression).getElementsByTagName('source')
    src                       = Source(src)
    
    (spectrumXML,)            = minidom.parseString(spectrum).getElementsByTagName('spectrum')
    src.spectrum              = Function(spectrumXML)
    src.deleteChildElements('spectrum')
    src.node.appendChild(src.spectrum.node)
    
    (func,)                   = minidom.parseString(diffuse).getElementsByTagName('spatialModel')
    src.spatialModel          = Function(func)
    src.deleteChildElements('spatialModel')
    src.node.appendChild(src.spatialModel.node)

    return src
pass

class GenericSource(object):
  def __init__(self):
    pass
  
  def getXML(self):
    uglyxml                   = self.source.node.toxml()
    xml                       = uglyxml.replace('<?xml version="1.0" ?>','')
    xml                       = xml.replace("<spatialModel","\n   <spatialModel")
    xml                       = xml.replace("<spectrum","   <spectrum")
    xml                       = xml.replace("</source","\n</source")
    #Remove repetite blanck lines
    xml                       = "\n".join(filter(lambda x:x.replace(" ",'')!="",xml.split("\n")))
    return "%s\n" % xml
  pass 
pass

def myPtSrc(spectrumFunction):
    name = ""
    
    src = '\n'.join( (('<source name= "%s" ' % name) + 'type="PointSource">',
                      '   <spectrum type="PowerLaw2"/>',
                      '   <!-- point source units are cm^-2 s^-1 MeV^-1 -->',
                      '   <spatialModel type="SkyDirFunction"/>',
                      '</source>\n') )
    src = minidom.parseString(src).getElementsByTagName('source')[0]
    src = Source(src)
    
    if(spectrumFunction not in availableSourceSpectra.keys()):
      raise RuntimeError("Spectrum function %s is not available. Available functions are: %s" %(spectrumFunction,
                                                                                              ",".join(availableSourceSpectra.keys())
                                                                                              ))
    
    src.spectrum = availableSourceSpectra[spectrumFunction]()
    src.deleteChildElements('spectrum')
    src.node.appendChild(src.spectrum.node)
    
    src.spatialModel = SkyDirFunction()
    src.deleteChildElements('spatialModel')
    src.node.appendChild(src.spatialModel.node)

    return src


class PointSource(GenericSource):
  def __init__(self,ra,dec,name='GRB',spectrumFunction='PowerLaw2'):
    
    self.source                        = myPtSrc(spectrumFunction)
    self.source.name                   = name
    
    if(spectrumFunction.lower()=='powerlaw2'):
      #Some pre-defined values for GRBs
      self.source.spectrum.Integral.max  = 1e5
      self.source.spectrum.Integral.min  = 1e-6
      self.source.spectrum.Integral.scale = 1e-03
      self.source.spectrum.Integral.value = 0.01
    
      self.source.spectrum.Index.max      = 0.01
      self.source.spectrum.Index.min      = -6.0
      self.source.spectrum.Index.value    = -2.0
    
      self.source.spectrum.LowerLimit.value = 100
      self.source.spectrum.LowerLimit.units  = ''
      #self.source.spectrum.LowerLimit.node.setAttribute('units','MeV')
      self.source.spectrum.UpperLimit.max   = 500000
      self.source.spectrum.UpperLimit.value = 100000
      self.source.spectrum.UpperLimit.units  = ''
      #self.source.spectrum.UpperLimit.node.setAttribute('units','MeV')
    
      self.source.spectrum.setAttributes()
    
    elif(spectrumFunction.lower()=='plsuperexpcutoff'):
    
      #Pre-defined values for Solar Flares
    
      self.source.spectrum.Prefactor.value = 1e-5
      self.source.spectrum.Prefactor.max = 1e6
      self.source.spectrum.Prefactor.min = 1e-6
      self.source.spectrum.Prefactor.scale = 0.001
      
      self.source.spectrum.Index1.value = -1.5
      self.source.spectrum.Index1.max = 5
      self.source.spectrum.Index1.min = -5
      self.source.spectrum.Index1.scale = 1
      
      self.source.spectrum.Scale.value = 50
      self.source.spectrum.Scale.max = 2000
      self.source.spectrum.Scale.min = 30
      self.source.spectrum.Scale.scale = 1
      
      self.source.spectrum.Cutoff.value = 300
      self.source.spectrum.Cutoff.max = 1e5
      self.source.spectrum.Cutoff.min = 30
      self.source.spectrum.Cutoff.scale = 1
      
      self.source.spectrum.Index2.value = 1.0
      self.source.spectrum.Index2.max = 5
      self.source.spectrum.Index2.min = -5
      self.source.spectrum.Index2.scale = 1
      self.source.spectrum.Index2.free = 0
      
      self.source.spectrum.setAttributes()
      
    pass
    
    self.source.spatialModel.RA.value  = ra
    self.source.spatialModel.DEC.value = dec
    self.source.spatialModel.setAttributes()
    self.source.setAttributes()
    
  pass 
pass

class IsotropicPowerlaw(GenericSource):
  def __init__(self,name="ParticleBackground"):
    self.source               = DiffuseSrc()
    self.source.name          = name
    
    self.source.spectrum.Prefactor.scale = 1e-06
    self.source.spectrum.Prefactor.value = 1.0
    self.source.spectrum.Prefactor.min   = 0.0
    self.source.spectrum.Prefactor.max   = 1e6
    self.source.spectrum.Prefactor.free  = 1
    
    self.source.spectrum.Index.max       = 1.0
    self.source.spectrum.Index.min       = -10
    self.source.spectrum.Index.value     = -1.5
    self.source.spectrum.Index.free      = 1
    
    self.source.spectrum.setAttributes()
    
    self.source.setAttributes()
  pass 
pass

class TemplateFile(GenericSource):
  def __init__(self,name,irf,constructorFunction,sysError=0.15,statError=0):
    self.source               = constructorFunction(irf)
    self.source.name          = name
    self.source.sysErr        = '%s' % sysError
    self.source.node.setAttribute('sysErr','%s' % sysError)
    self.source.statErr       = '%s' % statError
    self.source.node.setAttribute('statErr','%s' % statError)
    self.source.setAttributes()
  pass
  
  def fixNormalization(self):
    self.source.spectrum.Value.free = 0
    self.source.spectrum.setAttributes()
    self.source.setAttributes()
  pass
  
  def freeNormalization(self):
    self.source.spectrum.Value.free = 1
    self.source.spectrum.setAttributes()
    self.source.setAttributes()  
  pass
pass

class GalaxyAndExtragalacticDiffuse(TemplateFile):
  def __init__(self,irf,ra,dec,rad):
    TemplateFile.__init__(self,"GalacticTemplate",irf,
                          lambda irf:DiffuseSrcTemplateFunc(irf,ra,dec,rad))
  pass
pass

class IsotropicTemplate(TemplateFile):
  def __init__(self,irf):
    TemplateFile.__init__(self,"IsotropicTemplate",irf,IsotropicTemplateFunc,0.1)
  pass
pass

class BKGETemplate(TemplateFile):
  def __init__(self,filteredEventFile,ft2,tstart,tstop,triggerName,triggertime):
    #Make the BKGE estimate
    thisBkge                  = bkge.BKGE(filteredEventFile,ft2,triggerName,triggertime,os.getcwd())
    template,statErr,sysErr   = thisBkge.makeLikelihoodTemplate(tstart,tstop)
    os.environ['THISBKGE']    = os.path.abspath(template)
    print(template)
    if(os.path.exists(os.environ['THISBKGE'])==False):
      raise RuntimeError("The background estimator BKGE has failed!")
    TemplateFile.__init__(self,"IsotropicTemplate",'BKGE',IsotropicTemplateFunc,sysErr,statErr)
  pass
pass

class catalog_2FGL(object):
  def __init__(self,xmlfile):
    self.tree                 = ET.parse(xmlfile)
  pass
  
  def getXmlForSourcesInTheROI(self,ra,dec,rad,output,exposure):
    #Loop the tree and remove all sources more than rad away from the center
    #of the ROI
    root                      = self.tree.getroot()
    srcs                      = 0
    for source in root.findall('source'):      
      spatialModel            = source.findall('spatialModel')[0]
      
      #Remove point sources which cannot contribute any photon given the exposure
      aeff                    = 0.6e4 #cm2
      npred                   = float(source.get('Flux100'))*exposure*aeff
      if(source.get('type')=='PointSource' and npred < 1):
        root.remove(source)
        continue
      pass
      
      if(source.get('type')=='PointSource'):
        #Get coordinates of this point source
        coords                  = {}
        for p in spatialModel.iter('parameter'):
          coords[p.get('name').lower()] = float(p.get('value'))
        pass
        thisRa                  = coords['ra']
        thisDec                 = coords['dec']
        
        thisDist                = getAngularDistance(ra,dec,thisRa,thisDec)

        if(float(thisDist) >= float(rad)):
          #Remove this source
          root.remove(source)
        else:
          print("Keeping point source %s (%4.2f deg away)..." %(source.get('name'),float(thisDist)))
          #Fix all parameters
          specModel             = source.findall('spectrum')[0]
          for p in specModel.findall('parameter'):
            p.set('free','0')
          pass
          srcs                 += 1
      elif(source.get('type')=='DiffuseSource'):
        #Get coordinates of the center of this diffuse source
        thisRa                  = float(source.get('RA'))
        thisDec                 = float(source.get('DEC'))
        
        thisDist                = getAngularDistance(ra,dec,thisRa,thisDec)

        #Remove source if its center is more than twice its size out of the ROI
        if(float(thisDist) >= float(rad)+2*float(source.get('Extension'))):
          root.remove(source)
        else:
          #Fix all parameters
          specModel             = source.findall('spectrum')[0]
          for p in specModel.findall('parameter'):
            p.set('free','0')
          pass
          #Now correct the name of the FITS template so that the likelihood
          #will find it
          spatialModel          = source.findall('spatialModel')[0]
          filename              = spatialModel.get('file')
          templatesPath         = os.path.join(os.path.join(getDataPath(),'templates'))
          newFilename           = os.path.abspath(os.path.join(templatesPath,filename))
          spatialModel.set('file','%s' % newFilename)
          srcs                 += 1          
          print("Keeping diffuse source %s (%4.2f deg away) using template %s..." %(source.get('name'),float(thisDist),newFilename))
      else:
        print("WTF")
        raise
    pass
    print("Kept %s point sources from the 2FGL catalog" %(srcs))
    self.tree.write(output)
  pass
pass

class LikelihoodModel(object):
  def __init__(self):
    self.sources              = []  
  pass
  
  def addSources(self,*kwargs):
    '''
    Usage: model.addSources(IsotropicPowerlaw(),GalaxyAndExtragalacticDiffuse(),GRB(ra,dec))
    '''
    for source in kwargs:
      self.sources.append(source)
  pass
  
  def writeXML(self,filename):
    f                         = open(filename,'w+')
    f.write('<source_library title="source library">\n\n\n')
    for src in self.sources:
      f.write("%s\n\n" % src.getXML())
    pass
    f.write('</source_library>\n')
    f.close()
  pass
  
  def add2FGLsources(self,ra,dec,radius,filename,exposure):
    #Add all point sources in the 2FGL catalog with an angular distance less than 'radius'
    #from the given Ra,DEC\
    dataPath                  = getDataPath()
    fgl                       = catalog_2FGL(os.path.join(dataPath,'gll_psc_v07.xml'))
    tmpname                   = '__2fgl_sources.xml'
    fgl.getXmlForSourcesInTheROI(float(ra),float(dec),radius,tmpname,exposure)
    #Now merge the two trees
    tree                      = ET.parse(filename)
    root                      = tree.getroot()
    root.extend(ET.parse(tmpname).getroot())
    f                         = open(filename,'w+')
    tree.write(f)
    f.close()
    os.remove(tmpname)
  pass
pass

class SourceStruct(object):
  def __init__(self,name,srctype,ra,dec,flux=0,fluxError=0,photonFlux=0,photonFluxError=0,photonIndex=0,photonIndexError=0,TS=0):
    self.name                 = name
    self.type                 = srctype
    self.ra                   = float(ra)
    self.dec                  = float(dec)
    self.flux                 = flux
    self.fluxError            = fluxError
    self.photonFlux           = photonFlux
    self.photonFluxError      = photonFluxError
    self.photonIndex          = photonIndex
    self.photonIndexError     = photonIndexError
    self.TS                   = TS
  pass
pass

class LikelihoodResultsPrinter(object):
  def __init__(self,likelihoodObject,emin=100,emax=100000):
    self.likelihoodObj          = likelihoodObject
    self.emin                   = float(emin)
    self.emax                   = float(emax)
  pass
  
  def niceXMLprint(self,inputxmlmodel,tsmin=20,phIndexForUL=-2.05):
    tree                        = ET.parse(inputxmlmodel)
    root                        = tree.getroot()
    
    resultsStrings              = []
    
    def append(message):
      resultsStrings.append(message)
    
    append("|%20s|%15s|%10s|%12s|%10s|%6s|" %(20*'-',15*'-',10*'-',10*'-',10*'-',6*'-'))
    append("|%20s|%15s|%10s|%12s|%10s|%6s|" %('Source name','Par. Name','Value','Error','Units','TS'))
    append("|%20s|%15s|%10s|%12s|%10s|%6s|" %(20*'-',15*'-',10*'-',12*'-',10*'-',6*'-'))
    
    listOfSources             = []
    nNonPrinted               = 0
    
    allSources                = root.findall('source')
        
    #Count the total number of free parameters
    nFreeParameters           = 0
    for source in allSources:
      sourceName                = source.get('name')
      thisSrcNfree              = self.likelihoodObj.model[sourceName].src.getSrcFuncs()['Spectrum'].getNumFreeParams()
      nFreeParameters          += thisSrcNfree
        
    for source in allSources:
      sourceName                = source.get('name')
      sourceType                = source.get('type')
      
      #We need to know if removing this source will remove all the free parameters.
      #If that's the case, the TS computation with reoptimize=True will crash gtburst,
      #because minuit will throw a fatal error complaining about a fit without free parameters
      thisSrcNfree              = self.likelihoodObj.model[sourceName].src.getSrcFuncs()['Spectrum'].getNumFreeParams()
      
      if(thisSrcNfree == nFreeParameters):
        
        reoptimize              = False
      
      else:
        
        reoptimize              = True
        
      pass
         
      TS                        = max(0,self.likelihoodObj.Ts(sourceName,reoptimize=reoptimize,MaxIterations=10000))
      
      #energy flux
      MeVtoErg                  = 1.60217646E-6
      upperLimitComputed        = False
      if(math.ceil(TS) >= tsmin or sourceName.find('2FGL')>=0 or source.get('type')!='PointSource'):
        flux                    = '%10.3g' % (self.likelihoodObj.energyFlux(sourceName,self.emin,self.emax)*MeVtoErg)
        try:
          fluxError             = '%10.3g' % (self.likelihoodObj.energyFluxError(sourceName,self.emin,self.emax)*MeVtoErg)
        except:
          fluxError             = 'n.a.'
        phflux                  = '%10.3g' % (self.likelihoodObj.flux(sourceName,self.emin,self.emax))
        try:
          phfluxError           = '%10.3g' % (self.likelihoodObj.fluxError(sourceName,self.emin,self.emax))
        except:
          phfluxError           = 'n.a.'
      else:
        if(tsmin==0):
          flux                  = '%10.3g' % (self.likelihoodObj.energyFlux(sourceName,self.emin,self.emax)*MeVtoErg)
          fluxError             = 'not computed'
          phflux                = '%10.3g' % (self.likelihoodObj.flux(sourceName,self.emin,self.emax))
          phfluxError           = 'not computed'
        else:
          #Upper limit for point sources not in the 2FGL (i.e., the GRB)
          #Fixing the photon index to -2
          import UpperLimits
          if(phIndexForUL!=-2):
            index                 = phIndexForUL
            conv                  = (1.+index)/(2.0+index)*(pow(self.emax,index+2)-pow(self.emin,index+2))/(pow(self.emax,index+1)-pow(self.emin,index+1))
          else:
            index                 = -2.0
            conv                  = (self.emin)*(self.emax)/(self.emax-self.emin)*numpy.log(self.emax/self.emin)
          self.likelihoodObj[sourceName].src.spectrum().parameter('Index').setValue(index)
          self.likelihoodObj[sourceName].src.spectrum().parameter('Index').setFree(0)
          ulc                   = UpperLimits.UpperLimits(self.likelihoodObj)
          ul,integr             = ulc[sourceName].bayesianUL(emin=self.emin, emax=self.emax,cl=0.95)          
          ule                   = ul*conv
          flux                  = "< %8.3g" %(ule*MeVtoErg)
          fluxError             = 'n.a.'
          phflux                = "< %8.3g" %(ul)
          phfluxError           = 'n.a.'
          upperLimitComputed    = True
        pass
      pass
      
      #Get RA,Dec for this source
      spatialModel            = source.findall('spatialModel')[0]
      
      #Skip extended sources 
      if(source.get('type')=='PointSource'):
        #Get coordinates of this point source
        coords                  = {}
        for p in spatialModel.iter('parameter'):
          coords[p.get('name').lower()] = float(p.get('value'))
        pass
        thisRa                  = coords['ra']
        thisDec                 = coords['dec']
      else:
        thisRa                  = 0
        thisDec                 = 0
      pass
        
      if(sourceName.find('2FGL')>=0 and TS < 1):
        #Do not print non-detected 2FGL sources
        listOfSources.append(SourceStruct(sourceName,sourceType,thisRa,thisDec,flux,fluxError,0,0,TS))
        nNonPrinted            += 1
        continue
      pass
      
      append("|%-20s|%15s|%10s|%12s|%10s|%6i|" %(sourceName,'','','','',math.ceil(TS)))
      photonIndex               = 'n.a.'
      photonIndexError          = 'n.a.'
      for par in source.find('spectrum').iter('parameter'):
        name                    = par.get('name')
        free                    = par.get('free')
        
        if(name=='Integral'):
          name                  = "Integral"
          units                 = 'ph./cm2/s'
        elif(name=='LowerLimit' or name=='UpperLimit'):
          units                 = "MeV"
        else:
          units                 = '-'
        pass
        
        value                   = '%10.3g' % (float(par.get('value'))*float(par.get('scale')))
        try:
          error                 = '%12.3g' % (float(par.get('error'))*float(par.get('scale')))
        except:
          error                 = '%12s' %('n.a. (fixed)')
        
        if(name.lower()=='index'):
          photonIndex           = value
          photonIndexError      = error
        
        if(not upperLimitComputed):
          append("|%20s|%15s|%10s|%12s|%10s|%6s|" %('',name,value,error,units,''))
      pass
      
      append("|%20s|%15s|%10s|%12s|%10s|%6s|" %('','Energy flux',flux,fluxError,'erg/cm2/s',''))
      append("|%20s|%15s|%10s|%12s|%10s|%6s|" %('','Photon flux',phflux,phfluxError,'ph./cm2/s',''))
      listOfSources.append(SourceStruct(sourceName,sourceType,thisRa,thisDec,flux,fluxError,phflux,phfluxError,photonIndex,photonIndexError,TS))
    pass
    append("-%20s-%15s-%10s-%12s-%10s-%6s-\n" %(20*'-',15*'-',10*'-',12*'-',10*'-',6*'-'))
    if(nNonPrinted!=0):
      append("*** plus %s 2FGL sources with TS<1 (not printed to save space)" %(nNonPrinted))
    append("*** All fluxes and upper limits have been computed in the %s - %s energy range." %(self.emin,self.emax))
    append("*** Upper limits (if any) are computed assuming a photon index of %3.1f, with the 95 %s c.l." %(phIndexForUL,'%'))
          
    print("\n".join(resultsStrings))
    
    self.resultsStrings = "\n".join(resultsStrings)
    
    return listOfSources
  pass
  
pass

def optimizeBins(like,energies,sourceName,minTs=20,minEvt=3):
  if(len(energies)<=minEvt*2):
    raise RuntimeError("Not enough events to build a SED!")
  #Reversed array of energies (so we start binning from the top!)
  energies                    = numpy.array(sorted(energies)[::-1])
  #Get the first minEvt photons
  boundaries                  = [float(energies[0])+1]
  curIdx                      = minEvt-1  
  thisTs                      = 0
  #Compute the TS here
  while(1==1):
    curIdx                   += 1
    if(curIdx>=len(energies)):
      #Make sure the last boundary corresponds to the last photons
      boundaries[-1]          = float(energies[-1]-1)
      #Make sure we have more than minEvt events even in the last bin
      mask                    = (energies > boundaries[-1]) & (energies <= boundaries[-2])
      if(thisTs<minTs):
        #Merge the last bin with the preceding one
        boundaries            = numpy.delete(boundaries,1)
      break
    pass
    
    
    putativeBoundary          = float(energies[curIdx-1])
    try:
      putativeBoundary2       = float(energies[curIdx])
    except:
      putativeBoundary2       = putativeBoundary-1
    pass
    #Make the boundary at half way between the photons, so we are sure they will be selected
    putativeBoundary          = putativeBoundary - (putativeBoundary-putativeBoundary2)/2.0
    print("Trying bin %s-%s" %(putativeBoundary,boundaries[-1]))
    like.setEnergyRange(float(putativeBoundary),float(boundaries[-1]))
    thisTs                    = like.Ts(sourceName,reoptimize=True)
    print("TS = %s" %(thisTs))
    if(thisTs >= minTs):
      boundaries.append(putativeBoundary)
      mask                    = (energies > boundaries[-1]) & (energies <= boundaries[-2])
      print("\n==> Accepted bin %s-%s with TS = %5.2f and %s events\n" %(boundaries[-1],boundaries[-2],thisTs,len(energies[mask])))
      
      curIdx                 += (minEvt-1)
      continue
    else:
      continue
  pass
  return boundaries[::-1]
pass

def getSignalToNoise(like,e1,e2,sourceName):
  Nback = getExpectedBackgroundCounts(like,e1,e2,sourceName)
  Nsrc  = like[sourceName].src.Npred(e1,e2)
  return Nsrc

def getExpectedBackgroundCounts(like,e1,e2,sourceName):
    N                         = 0
    for name in like.sourceNames():
        if(name==sourceName):
            continue
        else:
            N                += like[name].src.Npred(e1,e2)
        pass
    pass
    return N
pass
