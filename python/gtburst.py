#!/usr/bin/env python
#Author: Giacomo Vianello (giacomov@slac.stanford.edu)

from GtBurst import version
packageName                   = version.getPackageName()
packageVersion                = version.getVersion()
GUIname                       = "Fermi Burst Analysis GUI"

import sys
import types
sys.stderr.write("\nLoading %s v. %s " %(packageName,packageVersion))
import matplotlib
sys.stderr.write(".")
matplotlib.use('TkAgg')
matplotlib.rcParams['font.size'] = 8

import time
from Tkinter import *
sys.stderr.write(".")
import math, subprocess
import os,re
import traceback
import collections
import glob
import shelve
import webbrowser
import pyfits,numpy
sys.stderr.write(".")

import matplotlib.pyplot as plt
plt.ion()
sys.stderr.write(".")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2TkAgg
from matplotlib.figure import Figure
from matplotlib import image
from tkSimpleDialog import askfloat
from GtBurst import fancyFileDialogs
#from tkFileDialog import askopenfilename
#from tkFileDialog import askdirectory
from tkMessageBox import showerror, showinfo, askyesno
sys.stderr.write(".")

from GtBurst import commandDefiner
from GtBurst import ConsoleText
from GtBurst import AutoHideScrollbar
from GtBurst import updater

from GtBurst import dataHandling

from GtBurst import IRFS
from GtBurst.commands.gtllebin import thisCommand as gtllebin
from GtBurst.commands.gtllebkg import thisCommand as gtllebkg
from GtBurst.commands.gtllesrc import thisCommand as gtllesrc
from GtBurst.commands.gtllesrcbindef import thisCommand as gtllesrcbindef
from GtBurst.commands.gtllebkgbindef import thisCommand as gtllebkgbindef
from GtBurst.commands.gtllebkgGUI import thisCommand as gtllebkgGUI
from GtBurst.commands.gtdocountsmap import thisCommand as gtdocountsmap
import GtBurst.commands.gtbuildxmlmodel
from GtBurst.commands.gtbuildxmlmodel import thisCommand as gtbuildxmlmodel
from GtBurst.commands.gtdolike import thisCommand as gtdolike
from GtBurst.commands.gtdotsmap import thisCommand as gtdotsmap
from GtBurst.commands.gtconvertxmlmodel import thisCommand as gtconvertxmlmodel
from GtBurst.commands.gtdosimulation import thisCommand as gtdosimulation
from GtBurst.commands.gteditxmlmodel import thisCommand as gteditxmlmodel
from GtBurst.commands.gteditxmlmodelsim import thisCommand as gteditxmlmodelsim
from GtBurst.commands.gtinteractiveRaDec import thisCommand as gtinteractiveRaDec

  
from GtBurst import angularDistance
from GtBurst.InteractiveFt1Display import InteractiveFt1Display
sys.stderr.write(".")
#from GtBurst import do_gbm
from GtBurst.CommandPipeline import CommandPipeline
from GtBurst.TransientSource import TransientSource
from GtBurst.Dataset import Dataset
from GtBurst.Configuration import Configuration
from GtBurst.EntryPoint import EntryPoint
from GtBurst.SubWindow import SubWindow
from GtBurst.fontDefinitions import *
from GtBurst.TriggerSelector import TriggerSelector
from GtBurst.HyperlinkManager import HyperlinkManager
from GtBurst import getLLEfiles
from GtBurst import getGBMfiles
from GtBurst import downloadTransientData
from GtBurst.dataHandling import _getLatestVersion
from GtBurst.GtBurstException import GtBurstException
from GtBurst.getDataPath import getDataPath

sys.stderr.write(". done \n")
if(GtBurst.commands.gtbuildxmlmodel.bkge.active):
  sys.stderr.write("\n-- Background estimator available --\n")
knownDetectors                  = ['n0','n1','n2','n3','n4','n5','n6','n7','n8','n9','na','nb','b0','b1',"LAT","LAT-LLE"]

#With this MetaClass a decorator (exceptionHandlerDecorator) will be applied to all methods
#of the class GUI. That decorator will catch all exceptions not caught by the methods,
#so that the program won't crash if something nasty happens

class MetaForExceptions(type):
    def __new__(cls, name, bases, attrs):

      for attr_name, attr_value in attrs.iteritems():
         if isinstance(attr_value, types.FunctionType):
            attrs[attr_name] = cls.exceptionHandlerDecorator(attr_value)

      return super(MetaForExceptions, cls).__new__(cls, name, bases, attrs)

    @classmethod
    def exceptionHandlerDecorator(cls,method):
      def handle_exception(*args,**kwargs):
        
        try:
          
          return method(*args,**kwargs)
        
        except GtBurstException as gte:
        
          # My exception handling:
          #Flush stdout so the exception is always shown at the end
          sys.stdout.flush()
          showerror("Error","%s" % (gte.longMessage))
        
        except:
          filename, line, dummy, dummy = traceback.extract_stack().pop()
          filename                     = os.path.basename( filename )
                
          msg                          = ("Snap! An unhandled exception has occurred at line %s of file %s.\n\n" %(line,filename) +
                                          "The program will try to continue running. If you think this is a bug, send a message" +
                                          " to fermihelp@milkyway.gsfc.nasa.gov attaching your gtburst.log file.\n\n"+
                                          "The full traceback has been saved to the log and printed in the console.")
          showerror("Unhandled exception",msg)
          
          dataHandling.exceptionPrinter(msg,traceback.format_exc(None))
        pass
      return handle_exception
    pass
pass

class GUI(object):
  __metaclass__               = MetaForExceptions
  
  def __init__(self):
    self.configuration        = Configuration()
    #Figure out where are the data
    import GtBurst
    path                      = GtBurst.__file__
    self.installationPath     = os.path.join(os.path.sep.join(path.split(os.path.sep)[0:-3]))
    self.dataPath             = getDataPath()
    self.datasets             = []
    self.object               = TransientSource()
    self.console              = None
    self.eventLock            = False
    self.addrmfWarning        = True
    self.main()
  pass
  
  def _findOtherFiles(self,cspecFile,parent):    
    #Get the root (something like bn100724009_v03)
    filename                  = os.path.abspath(os.path.expanduser(cspecFile))
    directory                 = os.path.dirname(os.path.abspath(filename))
    
    #LLE or GBM?
    prefix                    = os.path.basename(filename).split("_")[0]
    if(prefix=="gll"):
      #LLE or Transient
      if(filename.find("_tr_")>=0):
        #Transient data
        rootName              = "_".join(os.path.basename(filename).split("_")[2:5]).split(".")[:-1]
        rootName              = ".".join(rootName)
        detector              = "LAT"
        trigger               = rootName.split("_")[1]
      else:
        #LLE data
        rootName              = "_".join(os.path.basename(filename).split("_")[2:4]).split(".")[0]
        rootName              = "_".join(os.path.basename(filename).split("_")[2:5]).split(".")[:-1]
        rootName              = ".".join(rootName)
        detector              = "LAT-LLE"
        trigger                 = rootName.split("_")[0]
      pass
            
      triggered               = True
      triggerTime             = dataHandling.getTriggerTime(filename)
    elif(prefix=="glg"):
      #GBM
      rootName                = "_".join(os.path.basename(filename).split("_")[2:5]).split(".")[0]
      detector                = rootName.split("_")[0]
      trigger                 = rootName.split("_")[1]
      
      #Open the trigdat file and check if this detector was triggered or not
      try:
        trigdat                 = pyfits.open(_getLatestVersion(os.path.join(directory,"glg_trigdat_all_%s.fit" % "_".join(rootName.split("_")[1:]))))
        det_mask                = trigdat[0].header['DET_MASK']
        triggerTime             = dataHandling.getTriggerTime(filename)
        if(triggerTime==-1):
          triggerTime           = trigdat[0].header['TRIGTIME']
        thisDetIdx              = knownDetectors.index(detector)
        triggered               = bool(int(det_mask[thisDetIdx]))
        trigdat.close()
      except:
        #Do not fail if for some reason the code above does not succeed (for example
        #no trigcat is available)
        #Use a placeholder for the moment, later on I will check again on the
        #data files
        triggerTime             = -1
        triggered               = False  
    else:
      showerror("Unknown file", "The file %s is neither a LLE file nor a GBM file. You have to manually select other data." % lleFile,parent=parent)
      raise ValueError("Unknown file")
    pass
    
    dataset                   = Dataset(detector,trigger,triggerTime,triggered)
    
    try:
      dataset['cspecfile']    = _getLatestVersion(os.path.join(directory,"%s_cspec_%s.pha" %(prefix,rootName)))
    except:
      showerror("Error","File %s do not follow naming standards. Use the function 'Load custom dataset' from the menu file instead." %(filename),parent=parent)
      raise RuntimeError("File %s do not follow naming standards" %(filename))
    trigTime                  = dataHandling.getTriggerTime(dataset['cspecfile'])
    if(trigTime!=-1):
      dataset.triggerTime     = trigTime
    pass
      
    if(prefix=="gll"):
      if(detector=="LAT"):
        dataset['eventfile']    = _getLatestVersion(os.path.join(directory,"%s_ft1_%s.fit" %(prefix,rootName)))
        dataset['ft2file']      = _getLatestVersion(os.path.join(directory,"%s_ft2_%s.fit" %(prefix,rootName)))
        dataset['rspfile']      = _getLatestVersion(os.path.join(directory,"%s_cspec_%s.rsp" %(prefix,rootName)))
      elif(detector=="LAT-LLE"):
        dataset['eventfile']    = _getLatestVersion(os.path.join(directory,"%s_lle_%s.fit" %(prefix,rootName)))
        dataset['ft2file']      = _getLatestVersion(os.path.join(directory,"%s_pt_%s.fit" %(prefix,rootName)))
        dataset['rspfile']      = _getLatestVersion(os.path.join(directory,"%s_cspec_%s.rsp" %(prefix,rootName)))
    elif(prefix=="glg"):
      try:
        dataset['eventfile']    = _getLatestVersion(os.path.join(directory,"%s_tte_%s.fit" %(prefix,rootName)))
      except:
        dataset.status        = "noTTE"
        dataset['eventfile']  = dataset['cspecfile']
      pass  
      dataset['ft2file']      = 'None'
      try:
        dataset['trigdat']    = _getLatestVersion(os.path.join(directory,"glg_trigdat_all_%s.fit" % "_".join(rootName.split("_")[1:])))
      except:
        pass
      try:
        #If there is no "addrmf" executables in the path, do not use the rsp2 as response, but the rsp
        if(dataHandling.testIfExecutableExists("addrmf")==None):
          if(self.addrmfWarning):
            showinfo("Addrmf missing",("The tool addrmf is not available!\n\naddrmf is part of the Heasarc FTOOLS "
                                     " (CALTOOLS subpackage), "
                                     "and is needed to handle .rsp2 files, which contain the response of GBM "
                                     "detectors as a function of time. \n\nYou can proceed without it: this tool"
                                     " will use .rsp files instead, which contain an averaged response. Therefore,"
                                     " depending on the burst and on the duration of the time interval for the"
                                     " spectral analysis, the results of the spectral analysis might be slightly off.\n\n"
                                     "If you want to perform spectral analysis with GBM data, installing"
                                     " the FTOOLS is strongly advised. You can find them here: "
                                     "http://heasarc.nasa.gov/lheasoft/\n\nThis message will be displayed once per session."), 
                                     parent=parent)
            self.addrmfWarning  = False
          pass
          #Raise an exception so the following except will run
          raise
        else:
          #Addrmf is installed. Use the rsp2
          dataset['rspfile']    = _getLatestVersion(os.path.join(directory,"%s_cspec_%s.rsp2" %(prefix,rootName)))
      except:
        try:
          dataset['rspfile']  = _getLatestVersion(os.path.join(directory,"%s_cspec_%s.rsp" %(prefix,rootName)))
        except:
          if('rspfile' in dataset.keys()):
            del dataset['rspfile']
          #I did not find any .rsp file nor any .rsp2 file
          dataset.status        = "noRESP"
        pass
      pass       
    pass
    
    #Check that the file exists
    for key,f in dataset.iteritems():
      if(key=='ft2file' and prefix=='glg'):
        #It's ok not having the FT2 file with GBM data
        continue
      if(os.path.exists(f)==False):
        showerror("I/O error", "Cannot open this file\n %s \nFile does not exist or it is not readable." % f,parent=parent)      
      pass
    pass
        
    return dataset,trigger,triggered
  pass
  
  def openWebLink(self,url):
    webbrowser.open(url,2)
  pass
  
  
  def updateRootStatusbar(self,message,hint=None):   
    if(message.find("TIP")>=0):
      message,hint            = message.split("TIP")
    self.bottomtext.config(state=NORMAL)
    self.bottomtext.delete(1.0,END)
    self.bottomtext.insert(1.0,message)
    if(hint!=None):
      self.bottomtext.insert(END,"\n\n")
      self.bottomtext.image_create(END, image=self.lightbulb)
      self.bottomtext.insert(END,hint)
    pass
    self.bottomtext.config(state=DISABLED)
  pass  
  
  def fillObjectInfo(self):
    #Read info of the objects from datafiles
    f                         = pyfits.open(self.datasets[0]['rspfile'])
    header                    = f[0].header
    
    for key in self.objectInfoEntries.keys():
      self.objectInfoEntries[key].entry.config(state='normal')      
      if(key=='name'):
        #Workaround for the OBJECT keyword, which is wrong in some files
        self.objectInfoEntries[key].variable.set(self.datasets[0].triggerName)
      elif(key=='date'):
        self.objectInfoEntries[key].variable.set(self.datasets[0].triggerTime)
      else:
        try:
          self.objectInfoEntries[key].variable.set(header[self.object.headerKeyword[key]])
        except:
          self.objectInfoEntries[key].variable.set('not available')
      #self.objectInfoEntries[key].entry.config(state='readonly')
    pass
    f.close()    
  pass
  
  def loadCustomDataset(self):
    customWindow              = SubWindow(self.root,transient=True,title="Custom dataset",
                                          initialHint="")
    customWindow.bottomtext.config(state="normal")
    customWindow.bottomtext.insert(1.0,"Warning: no check whatsoever will be performed on the files, be careful!\n\nPlease choose your data files.")
    customWindow.bottomtext.config(state="disabled")
    customWindow.bottomtext.image_create(1.0, image=self.exlamationmark)

    customWindow.window.geometry("800x450+20+20")

    entries                   = {}    
    entryFrame                = Frame(customWindow.frame)
    entryFrame.grid(column=0,row=0)
    entries['detname']        = EntryPoint(entryFrame,labeltext="Detector",
                                           textwidth=40,possibleValues=knownDetectors,initvalue='LAT')
    
    entries['triggerName']    = EntryPoint(entryFrame,labeltext="Source name (optional)",
                                           textwidth=40)
    
    entries['triggerTime']    = EntryPoint(entryFrame,labeltext="Trigger time (required if not in the file)",
                                           textwidth=40,initvalue=str(self.objectInfoEntries['date'].get()))
    
    entries['cspecfile']      = EntryPoint(entryFrame,labeltext="CSPEC file (required)",
                                           textwidth=40,initvalue='',
                                           directory=False,browser=True)
    
    entries['rspfile']        = EntryPoint(entryFrame,labeltext="Response file (RSP or RSP2)",
                                           textwidth=40,initvalue='',
                                           directory=False,browser=True)
    
    entries['eventfile']      = EntryPoint(entryFrame,labeltext="Event file (TTE or LLE, optional)",
                                           textwidth=40,initvalue='',
                                           directory=False,browser=True)
    
    entries['ft2file']        = EntryPoint(entryFrame,labeltext="FT2 file (needed for LAT data)",
                                           textwidth=40,initvalue='',
                                           directory=False,browser=True)
    
    buttonFrame               = Frame(customWindow.frame)
    buttonFrame.grid(column=0,row=1)
    saveButton                = Button(buttonFrame,text="Load", font=NORMALFONT,
                                       command=lambda: self._registerCustomDataset(entries,customWindow.window))
    saveButton.grid(row=0,column=0,sticky="NSWE")
    
    cancelButton              = Button(buttonFrame,text="Cancel", font=NORMALFONT,
                                  command=customWindow.window.destroy)
    cancelButton.grid(row=0,column=1,sticky="NSWE")
  pass
  
  def _registerCustomDataset(self,entries,parent):
    detector                  = entries['detname'].get()
    trigger                   = entries['triggerName'].get()
    
    #Check that files exists
    if not dataHandling._fileExists(entries['cspecfile'].get()):
      showerror("No CSPEC file","CSPEC file unspecified or not existent. Please correct it.")
      return
    if not dataHandling._fileExists(entries['rspfile'].get()):
      showerror("No RSP file","RSP file unspecified or not existent. Please correct it.")
      return
    if entries['eventfile'].get()!="" and (not dataHandling._fileExists(entries['eventfile'].get())):
      showerror("Wrong event file","Specified event file does not exists! Please correct it, or leave it empty.")
      return
    if entries['detname'].get().find("LAT")>=0 and (not dataHandling._fileExists(entries['ft2file'].get())):
      showerror("No FT2 file","If these are LAT data, you HAVE to provide an FT2 file.")
      return
    
    triggerTime               = None
    
    try:
      triggerTime               = float(entries['triggerTime'].get())
    except:
      #Try and read it from the event file
      f                       = pyfits.open(entries['eventfile'].get())
      if('TRIGTIME' in f[0].header.keys()):
        triggerTime             = float(f[0].header['TRIGTIME'])
      else:
        showerror("Error in the trigger time","Could not understand the trigger time. You did not specify the MET and it is not in the event file.",parent=parent)
        f.close()
        return
      pass
      f.close()
    pass
    
    if(trigger==''):
      try:
        trigger                 = pyfits.getval(entries['eventfile'].get(),'OBJECT')
        #Add 'bn' in front of the name if it begins with a number
        if(re.search('[0-9]',trigger[0])!=None):
          trigger               = 'bn%s' % trigger
      except:
        trigger                 = "Unknown"
    
    dataset                   = Dataset(detector,trigger,triggerTime,True)
    dataset['eventfile']      = entries['eventfile'].get()
    dataset['rspfile']        = entries['rspfile'].get()
    dataset['cspecfile']      = entries['cspecfile'].get()
    dataset['ft2file']        = entries['ft2file'].get()
    if entries['eventfile'].get()=="":
      dataset.status          = "noTTE"
    datasets                  = list(self.datasets)
    datasets.append(dataset)
    parValues                 = []
    for s in datasets:
      parValues.append(IntVar())
      parValues[-1].set(int(1))
    self.registerDatasets(datasets,parValues,parent,False)
  pass
  
  def changeTriggerTime(self):
    #No trigger time information at all!
    triggerTime = askfloat("Change trigger time","Please specify the new trigger time:",parent=self.root)
    if(triggerTime=='' or triggerTime==0 or triggerTime==None):
      sys.stderr.write("\nChange of trigger time canceled. Keeping the old value.\n")
      return
    for dataset in self.datasets:
      print("Using %s as trigger time for detector %s and object %s" %(triggerTime,dataset.detector,
                                                                        dataset.triggerName))
      dataset.triggerTime = triggerTime
    pass
    
    #Write the keyword UREFTIME in all the input data files, which I will use as 
    #reference time, to avoid overwriting the TRIGTIME keyword
    for dataset in self.datasets:
      for key in ['rspfile','cspecfile','eventfile']:
        f                     = pyfits.open(dataset[key],"update")
        f[0].header.set("UREFTIME",triggerTime)
        f.close()
      pass
    pass  
    
    #Update the status bar in the main window
    if(len(self.datasets)>0):     
      #Update the information on the object
      self.fillObjectInfo()
  pass
  
  def quit(self):
    try:
      self.console.stop()
    except:
      pass
    self.root.quit()
  pass
  
  def makeNavigationPlots(self):
    #Find if there is any available ft2 file
    #Search for LAT standard data
    LATdataset                = filter(lambda x:x.detector=="LAT",self.datasets)
    LLEdataset                = filter(lambda x:x.detector=="LAT-LLE",self.datasets)
    if(len(LATdataset)!=0):
      #We have LAT standard data
      ft2file                 = LATdataset[0]['ft2file']
    else:
      if(len(LLEdataset)==0):
        showerror("No LAT data","You need to load either LAT standard data or LLE data to produce navigation plots",parent=self.root)
        return
      else:
        #We have LLE data
        ft2file               = LLEdataset[0]['ft2file']
      pass
    pass
    #If we are here, we have an ft2 file
    
    ra_obj                    = float(self.objectInfoEntries['ra'].variable.get())
    dec_obj                   = float(self.objectInfoEntries['dec'].variable.get())
    triggerTime               = float(self.datasets[0].triggerTime)
    
    figure                    = dataHandling.makeNavigationPlots(ft2file,ra_obj,dec_obj,triggerTime)
    figure.canvas.draw()   
  pass
  
  def updateGtBurst(self):
    cwd                     = os.getcwd()
    os.chdir(self.installationPath)
    print("\nUpdating gtburst...")
    try:
      nUpdates                = updater.update()
    except:
      raise
    else:
      os.chdir(cwd)
      if(nUpdates==0):
        showinfo("No update","No update available at this moment!")
        print("No update available at this moment!")
      else:
        print("\nDone! %s files updated" % (nUpdates))
        showinfo("Restarting gtburst","Update finished! About to restart gtburst for the update to take effect.")
        reset()
      pass
    pass
  pass
  
  def OnFrameConfigure2(self,event):
    self.helptextCanvas.configure(scrollregion=self.helptextCanvas.bbox("all"))
  pass
  
  def OnFrameConfigure(self,event):
    self._canvas.configure(scrollregion=self._canvas.bbox("all"))
  pass
  
  def main(self):
    self.root                 = Tk()
    
    #Update $auto_path Tcl variable, so tcl will find my custom tcl scripts
    tclPath                   = os.path.join(self.dataPath,'tcl_extensions')
    path                      = os.path.join(tclPath,'msgcat')
    self.root.tk.eval("set auto_path [linsert $auto_path 0 %s]" %(path))
    path                      = os.path.join(tclPath,'fsdialog')
    self.root.tk.eval("set auto_path [linsert $auto_path 0 %s]" %(path))
    
    self.root.iconify()
    #self.root.geometry("1024x768+0+0")
    self.root.title("Fermi bursts analysis GUI")
    
    #Add the menubar
    menubar                   = Menu(self.root)
    filemenu                  = Menu(menubar, tearoff=0)
    filemenu.add_command(label="Load data from a directory...",
                               command=self.loadDataSetsFromAdirectory)
    filemenu.add_command(label="Load a custom dataset...",
                               command=self.loadCustomDataset)
    filemenu.add_command(label="Download datasets...",
                               command=self.downloadDataSet)
    filemenu.add_command(label="Change trigger time...",
                               command=self.changeTriggerTime)
    filemenu.add_command(label="Reset...",
                               command=reset)
    filemenu.add_command(label="Configuration...", command=self.configure)
    filemenu.add_command(label="Quit", command=self.quit)
    
    self.tasksmenu                 = Menu(menubar,tearoff=0)
    self.tasksmenu.add_command(label="Make likelihood analysis",
                          command=self.likelihoodAnalysis,
                          state=DISABLED) 
    self.tasksmenu.add_command(label="Find source with TS map",
                          command=self.tsmap,
                          state=DISABLED)
    self.tasksmenu.add_command(label="Interactively recenter ROI",
                          command=self.recenterROI,
                          state=DISABLED)
    #self.tasksmenu.add_command(label="Simulate GRB observation",
    #                      command=self.simulateObservation,
    #                      state=DISABLED)
    self.tasksmenu.add_command(label="Make spectra for XSPEC",
                          command=self.commandInterface,
                          state=DISABLED) 
                          
    toolsmenu                 = Menu(menubar,tearoff=0)
    toolsmenu.add_command(label="Make navigation plots (you need to load either LLE or standard LAT data)",
                          command=self.makeNavigationPlots) 
    updatemenu                = Menu(menubar,tearoff=0)
    updatemenu.add_command(label="Update to the latest version",command=self.updateGtBurst)
    
    menubar.add_cascade(label="File",menu=filemenu)
    menubar.add_cascade(label="Tasks",menu=self.tasksmenu)
    menubar.add_cascade(label="Tools",menu=toolsmenu)
    menubar.add_cascade(label="Update",menu=updatemenu)
    
    self.root.config(menu=menubar)
    
    #Load some icons
    self.lightbulb            = PhotoImage(file=os.path.join(self.dataPath,"lightbulb.gif"))
    self.exlamationmark       = PhotoImage(file=os.path.join(self.dataPath,"warning.gif"))
    
    #Fill the bottom frame
    #Canvas for the Fermi logo
    logoFilename              = os.path.join(self.dataPath,"fermiLogo.gif")
    logo                      = PhotoImage(file=logoFilename)
    logoLabel                 = Label(self.root, image=logo)
    #logoLabel.image           = logo
    #logoLabel.grid(row=2,column=0,sticky=W+E+N+S)
    #Console
    self.consoleFrame         = Frame(self.root)
    self.consoleFrame.grid(row=2,column=1,sticky=W+E+N+S)
    consoleScrollbar          = Scrollbar(self.consoleFrame,orient="vertical")
    self.console              = ConsoleText.ConsoleText(self.consoleFrame,
                                      yscrollcommand=consoleScrollbar.set,
                                      width=100,height=10,bg='white')
    consoleScrollbar.config(command=self.console.yview)
    self.console.grid(row=0,column=0,sticky=W+E+N+S)
    consoleScrollbar.grid(row=0,column=1,sticky=W+E+N+S)
    self.console.start()
    print("Welcome to the %s v. %s!\n\nCredits: G.Vianello (giacomov@slac.stanford.edu), N.Omodei (nicola.omodei@gmail.com)\n" %(GUIname,packageVersion))
    print("This software embeds:")
    print("-gtapps_mp by J. Perkins (http://fermi.gsfc.nasa.gov/ssc/data/analysis/user/)")
    print("-APlpy (http://aplpy.github.io/)")
    print("\nThese packages are property of the respective authors.")
    #Fill the mainFrame
    bigFrame                  = Frame(self.root)
    bigFrame.grid(row=0,column=0,rowspan=2,sticky=N+S+W+E)
    vscrollbar                = AutoHideScrollbar.AutoHideScrollbar(bigFrame)
    vscrollbar.grid(row=0, column=1, sticky=N+S)
    hscrollbar                = AutoHideScrollbar.AutoHideScrollbar(bigFrame, orient=HORIZONTAL)
    hscrollbar.grid(row=1, column=0, sticky=E+W)
    self._canvas                    = Canvas(bigFrame,
                                       yscrollcommand=vscrollbar.set,
                                       xscrollcommand=hscrollbar.set)
    self._canvas.grid(row=0, column=0,sticky=N+S+E+W)
    vscrollbar.config(command=self._canvas.yview)
    hscrollbar.config(command=self._canvas.xview)   
    self.root.grid_rowconfigure(0, weight=1)
    self.root.grid_columnconfigure(0, weight=1)
    bigFrame.grid_rowconfigure(0,weight=1)
    bigFrame.grid_columnconfigure(0,weight=1)
    
    self.userInteractionFrame = Frame(self._canvas,bd=0)
    self.userInteractionFrame.bind("<Configure>", self.OnFrameConfigure)
    
    
    #Help text
    self.bottomtextFrame      = Frame(self.root)
    self.bottomtextFrame.grid(row=2,column=0,sticky=W+E+N+S)
    helpscrollbar             = AutoHideScrollbar.AutoHideScrollbar(self.bottomtextFrame)
    self.helptextCanvas       = Canvas(self.bottomtextFrame,yscrollcommand=helpscrollbar.set)
    self.bottomtext           = Text(self.helptextCanvas, wrap='word', 
                                     font=COMMENTFONT,height=8,width=45,
                                     yscrollcommand=helpscrollbar.set)
    helpscrollbar.config(command=self.bottomtext.yview)
    self.bottomtext.grid(row=0,column=0,sticky=W+E+N+S)
    self.helptextCanvas.grid(row=0,column=0)
    helpscrollbar.grid(row=0,column=1,sticky=W+E+N+S)
    self.hyperlink            = HyperlinkManager(self.bottomtext)
    self.bottomtext.config(state=DISABLED) 
    
    descr = '''
    With this application you can download Fermi data for GRBs and Solar Flares, 
    compute source and background spectra for GBM and LAT/LLE data,
    perform likelihood analysis and 
    observation simulation with standard LAT data.'''
    
    self.updateRootStatusbar(" ".join(descr.split()),"To begin, click on the File menu.")
    self.userInteractionFrame.bind("<Configure>", self.OnFrameConfigure2)
    
    self.figureFrame          = Frame(self.root)
    self.figureFrame.grid(row=0,column=1,rowspan=2,sticky='nsew')
    self.figure               = Figure(dpi=100,figsize=(7.0,4))
    self.canvas               = FigureCanvasTkAgg(self.figure,
                                        master=self.figureFrame)
    self.canvas.get_tk_widget().grid(column=0,row=0,sticky='nsew')
    bigLogo                   = image.imread(os.path.join(self.dataPath,"glast_logo.png"))
    axes                      = self.figure.add_subplot(111)
    axes.set_axis_off()
    axes.imshow(bigLogo)
    self.canvas.show()    
    self.figToolbar           = NavigationToolbar2TkAgg(self.canvas,self.figureFrame)
    self.figToolbar.update()
    self.canvas._tkcanvas.pack(side=TOP,fill=BOTH,expand=True)
    
    #Set up the form for the dataset
    rightSubFrames            = []
    rightLabels               = []
    parValues                 = {}
    rightEntries              = []
    colWidth                  = 20
    
    self.objectInfoFrame      = Frame(self.userInteractionFrame)
    self.objectInfoFrame.grid(row=0,column=0,sticky=N+S+E+W)
    self.objectInfoEntries    = {}
    
    for parname,description in self.object.descriptions.iteritems():
      self.objectInfoEntries[parname] = EntryPoint(self.objectInfoFrame,
                                                   labeltext=description,
                                                   textwidth=colWidth,
                                                   initvalue=self.object[parname],
                                                   directory=False,
                                                   browser=False,
                                                   inactive=True)
    pass
    
    self.displayDetFrame      = None
    self._canvas.create_window(0, 0, anchor=NW, window=self.userInteractionFrame,height=400)
    self.userInteractionFrame.grid_rowconfigure(0, weight=1)
    self.userInteractionFrame.update_idletasks()
    self._canvas.config(scrollregion=self._canvas.bbox("all"))

    self.saveUserInteractionFrame()
  pass
  
  def tsmap(self):
    datasetsFilter            = lambda x:x.detector=="LAT"
    
    gtdocountsmap.definedParameters['ra'].type = commandDefiner.HIDDEN
    gtdocountsmap.definedParameters['ra'].value = self.objectInfoEntries['ra'].variable.get()
    
    gtdocountsmap.definedParameters['dec'].type = commandDefiner.HIDDEN
    gtdocountsmap.definedParameters['dec'].value = self.objectInfoEntries['dec'].variable.get()
    
    #gtdocountsmap.definedParameters['skybinsize'].type = commandDefiner.HIDDEN
    gtbuildxmlmodel.definedParameters['ra'].type = commandDefiner.HIDDEN
    gtbuildxmlmodel.definedParameters['ra'].value = self.objectInfoEntries['ra'].variable.get()
    
    gtbuildxmlmodel.definedParameters['dec'].type = commandDefiner.HIDDEN
    gtbuildxmlmodel.definedParameters['dec'].value = self.objectInfoEntries['dec'].variable.get()
    
    gtbuildxmlmodel.definedParameters['triggername'].type = commandDefiner.HIDDEN
    gtbuildxmlmodel.definedParameters['triggername'].value = self.objectInfoEntries['name'].variable.get()
    
    gteditxmlmodel.definedParameters['tkwindow'].value = self.root
    gteditxmlmodel.definedParameters['tkwindow'].type = commandDefiner.HIDDEN
    
    #Define commands and help string
    commands                  = []
    commands.append(gtdocountsmap)
    commands.append(gtbuildxmlmodel)
    commands.append(gteditxmlmodel)
    commands.append(gtdotsmap)
        
    finalProducts              = {}
    self.cleanUserInteractionFrame()
        
    self.stepByStep            = CommandPipeline(self.userInteractionFrame,
                                                 self.updateRootStatusbar,
                                                 commands,
                                                 self.datasets,
                                                 self.console,
                                                 finalProducts,
                                                 self.afterTSmap,
                                                 self.figure,
                                                 self.figureFrame,
                                                 self.canvas,
                                                 datasetsfilter=datasetsFilter)
    
  pass
  
  def afterTSmap(self,datasetsFilter=lambda x:True):
    self.fillUserInteractionFrame()
    self.writeDefaultHelpMessage()
    showinfo("Info","Note that the coordinates of the maximum of the TS map will NOT be used automatically.\n\nIf you want to use them, copy RA and Dec from the Console to the 'R.A. (J2000)' and 'Dec. (J2000)' entry on the upper left corner.")
    self.makeLightCurves()
  pass
  
  pass
  
  def recenterROI(self):
    datasetsFilter            = lambda x:x.detector=="LAT"
    
    gtdocountsmap.definedParameters['ra'].type = commandDefiner.HIDDEN
    gtdocountsmap.definedParameters['ra'].value = self.objectInfoEntries['ra'].variable.get()
    
    gtdocountsmap.definedParameters['dec'].type = commandDefiner.HIDDEN
    gtdocountsmap.definedParameters['dec'].value = self.objectInfoEntries['dec'].variable.get()
    
    #Define commands and help string
    commands                  = []
    commands.append(gtdocountsmap)
    commands.append(gtinteractiveRaDec)
        
    finalProducts              = {}
    self.cleanUserInteractionFrame()
        
    self.stepByStep            = CommandPipeline(self.userInteractionFrame,
                                                 self.updateRootStatusbar,
                                                 commands,
                                                 self.datasets,
                                                 self.console,
                                                 finalProducts,
                                                 self.recenterROIafterSkymap,
                                                 self.figure,
                                                 self.figureFrame,
                                                 self.canvas,
                                                 datasetsfilter=datasetsFilter)
    
  pass
  
  def recenterROIafterSkymap(self,datasetsFilter=lambda x:True):
    #Update RA and DEC
    dataset                   = filter(datasetsFilter,self.datasets)[0]
    if('user_ra' in dataset.keys()):
      user_ra                   = dataset['user_ra']
      user_dec                  = dataset['user_dec']
      
      self.objectInfoEntries['ra'].variable.set(str(user_ra))
      self.objectInfoEntries['dec'].variable.set(str(user_dec))
    else:
      showerror("Error","Something went wrong when recentering ROI...",parent=self.root)
    pass
    self.fillUserInteractionFrame()
    self.writeDefaultHelpMessage()
    self.makeLightCurves()
  pass
  
  def saveUserInteractionFrame(self):
    #Save all the fields in the userInteraction frame
    self.userInteractionFrameContent = []
    for child in self.userInteractionFrame.grid_slaves():
      self.userInteractionFrameContent.append(child)
    pass 
  pass
  
  def simulateObservation(self):
    datasetsFilter            = lambda x:x.detector=="LAT"
    datasets                  = filter(datasetsFilter,self.datasets)
    
    triggernamesim                     = "%ssim" % self.objectInfoEntries['name'].variable.get()
         
    #gtconvertxmlmodel.definedParameters['xmlmodel'].type = commandDefiner.HIDDEN
    #gtconvertxmlmodel.definedParameters['emin'].type     = commandDefiner.HIDDEN 
    #gtconvertxmlmodel.definedParameters['emax'].type     = commandDefiner.HIDDEN   
    gtdosimulation.definedParameters['triggertime'].type = commandDefiner.HIDDEN  
    gtdosimulation.definedParameters['triggertime'].value = self.objectInfoEntries['date'].variable.get()
    
    gtdosimulation.definedParameters['irf'].type         = commandDefiner.HIDDEN        
    gtdosimulation.definedParameters['outdir'].value     = os.path.join(self.configuration.get('dataRepository'),triggernamesim)
    
    #Add a predefined name for the simulated FT1 file
    for i,d in enumerate(self.datasets):
      if(not datasetsFilter(d)):
        continue
      else:
        self.datasets[i]['simeventfile'] = 'gll_ft1_tr_%s_v00.fit' %(triggernamesim)
    pass
    
    latdataset                = datasets[0]
    if('likexmlresults' in latdataset.keys()):
      gteditxmlmodelsim.definedParameters['likexmlresults'].value = latdataset['likexmlresults']
    
    gteditxmlmodelsim.definedParameters['tkwindow'].value = self.root
    gteditxmlmodelsim.definedParameters['tkwindow'].type = commandDefiner.HIDDEN
    

    #Define commands and help string
    commands                  = []
    commands.append(gteditxmlmodelsim)
    commands.append(gtconvertxmlmodel)
    commands.append(gtdosimulation)
            
    finalProducts              = {"Simulated ft1 file": 'simeventfile'}
    self.cleanUserInteractionFrame()
        
    self.stepByStep            = CommandPipeline(self.userInteractionFrame,
                                                 self.updateRootStatusbar,
                                                 commands,
                                                 self.datasets,
                                                 self.console,
                                                 finalProducts,
                                                 self.afterSimulation,
                                                 self.figure,
                                                 self.figureFrame,
                                                 self.canvas,
                                                 datasetsfilter=datasetsFilter)
    
  pass
  
  def afterSimulation(self,datasetsFilter=lambda x:True):
    self.fillUserInteractionFrame()
    self.writeDefaultHelpMessage()
    self.makeLightCurves()
  pass
  
  def likelihoodAnalysis(self):
    datasetsFilter            = lambda x:x.detector=="LAT"
    
    #Get the processing version for this LAT data
    reproc                    = pyfits.getval(filter(datasetsFilter,self.datasets)[0]['eventfile'],'PROC_VER',ext=0)
    
    gtdocountsmap.definedParameters['irf'].possibleValues = IRFS.PROCS[str(reproc)]
    
    gtdocountsmap.definedParameters['ra'].type = commandDefiner.HIDDEN
    gtdocountsmap.definedParameters['ra'].value = self.objectInfoEntries['ra'].variable.get()
    
    gtdocountsmap.definedParameters['dec'].type = commandDefiner.HIDDEN
    gtdocountsmap.definedParameters['dec'].value = self.objectInfoEntries['dec'].variable.get()
    
    #gtdocountsmap.definedParameters['skybinsize'].type = commandDefiner.HIDDEN
    gtbuildxmlmodel.definedParameters['ra'].type = commandDefiner.HIDDEN
    gtbuildxmlmodel.definedParameters['ra'].value = self.objectInfoEntries['ra'].variable.get()
    
    gtbuildxmlmodel.definedParameters['dec'].type = commandDefiner.HIDDEN
    gtbuildxmlmodel.definedParameters['dec'].value = self.objectInfoEntries['dec'].variable.get()
    
    gtbuildxmlmodel.definedParameters['triggername'].type = commandDefiner.HIDDEN
    gtbuildxmlmodel.definedParameters['triggername'].value = self.objectInfoEntries['name'].variable.get()
    
    gteditxmlmodel.definedParameters['tkwindow'].value = self.root
    gteditxmlmodel.definedParameters['tkwindow'].type = commandDefiner.HIDDEN
    
    #Define commands and help string
    commands                  = []
    commands.append(gtdocountsmap)
    commands.append(gtbuildxmlmodel)
    commands.append(gteditxmlmodel)
    commands.append(gtdolike)
        
    finalProducts              = {"Sky map": 'skymap',
                                  "Input XML model": 'xmlmodel',
                                  "Likelihood results (XML)": 'likexmlresults'}
    self.cleanUserInteractionFrame()
        
    self.stepByStep            = CommandPipeline(self.userInteractionFrame,
                                                 self.updateRootStatusbar,
                                                 commands,
                                                 self.datasets,
                                                 self.console,
                                                 finalProducts,
                                                 self.afterLikelihood,
                                                 self.figure,
                                                 self.figureFrame,
                                                 self.canvas,
                                                 datasetsfilter=datasetsFilter)
    
  pass
  
  def afterLikelihood(self,datasetsFilter=lambda x:True):
    self.fillUserInteractionFrame()
    self.writeDefaultHelpMessage()
    self.makeLightCurves()
  pass
  
  def run(self):
    #self.root.resizable(0,0)
    
    #Center the window on the screen
    self.root.update_idletasks()
    xp = (self.root.winfo_screenwidth() / 2) - (self.root.winfo_width() / 2)
    yp = (self.root.winfo_screenheight() / 2) - (self.root.winfo_height() / 2)
    self.root.geometry('{0}x{1}+{2}+{3}'.format(self.root.winfo_width(), self.root.winfo_height(),
                                                                        xp, yp))
    
    #If the user try to expand the window, only the canvas will expand
    Grid.rowconfigure(self.root,0,weight=1)
    Grid.columnconfigure(self.root,1,weight=1)
    Grid.rowconfigure(self.figureFrame,0,weight=1)
    Grid.columnconfigure(self.figureFrame,0,weight=1)
    
    Grid.rowconfigure(self.root,1,weight=0)
    Grid.columnconfigure(self.root,0,weight=0)
    Grid.rowconfigure(self.root,2,weight=0)
    Grid.columnconfigure(self.consoleFrame,0,weight=1)
    Grid.columnconfigure(self.consoleFrame,1,weight=0)
    Grid.rowconfigure(self.consoleFrame,0,weight=0)
    #self.root.grid_rowconfigure(self.figureFrame,row=0,weight=1)
    #self.figureFrame.grid_columnconfigure(self.figureFrame,column=0,weight=1)
    #self.figureFrame.grid_rowconfigure(self.figureFrame,row=0,weight=1)
    
    self.root.deiconify()
    try:
      self.root.mainloop()
    except:
      print("HEY!")
  pass
  
  def cleanUserInteractionFrame(self):
    for child in self.userInteractionFrame.grid_slaves():
      child.grid_remove()
    pass
  pass
  
  def fillUserInteractionFrame(self):
    self.cleanUserInteractionFrame()
    for child in self.userInteractionFrameContent:
      child.grid()
    pass
  pass
    
  def commandInterface(self):
    #Remove LAT Transient data from the datasets used for the spectral analysis,
    #since there is no point in doing the polynomial fit for those data
    datasetsFilter             = lambda x:x.detector!="LAT"
    
    datasets                   = filter(datasetsFilter,self.datasets)
    
    if(len(datasets)==0):
      showinfo("No suitable datasets","No suitable datasets for spectral analysis. You have to load either GBM or LAT/LLE data.",parent=self.root)
      return
      
    #Define commands and help string
    commands                  = []
    #Add the data selector for gtllescrbindef
    gtllesrcbindef.addParameter("dataset to use",
                                "Select the dataset to display for selecting the source interval",
                                commandDefiner.MANDATORY,
                                None,
                                partype=commandDefiner.PYTHONONLY,
                                possibleValues=map(lambda x:x.detector,datasets))
    commands.append(gtllesrcbindef)
    commands.append(gtllebkgGUI)
    commands.append(gtllesrc)
        
    finalProducts              = {"Observed spectrum": 'srcspectra',
                                  "Backgr. spectrum": 'bkgspectra',
                                  "Response": 'weightedrsp'}
    self.cleanUserInteractionFrame()
    
    
    self.stepByStep            = CommandPipeline(self.userInteractionFrame,
                                                 self.updateRootStatusbar,
                                                 commands,
                                                 datasets,
                                                 self.console,
                                                 finalProducts,
                                                 self.writeXspecScript,
                                                 self.figure,
                                                 self.figureFrame,
                                                 self.canvas,
                                                 datasetsfilter=datasetsFilter)
  pass

  def writeXspecScript(self,datasetsFilter=lambda x:True):
    self.fillUserInteractionFrame()
    self.writeDefaultHelpMessage()
    self.makeLightCurves()
    #Get the number of intervals
    try:
      with pyfits.open(self.datasets[0]['srcspectra']) as firstPha:
        bkgTest                   = self.datasets[0]['bkgspectra']
        rspTest                   = self.datasets[0]['rspfile']
        nIntervals                = len(firstPha['SPECTRUM',1].data)
    except:
      showerror("Error","Something went wrong when producing spectra.")
      return
    else:      
      for intID in range(1,nIntervals+1):
        #This method is called after the CommandPipeline has terminated
        f                         = open("loadData_%s_int%02i.xcm" %(self.datasets[0].triggerName,intID),"w+")
        
        for i,dataset in enumerate(self.datasets):
          if(not datasetsFilter(dataset)):
            continue
          else:
            f.write("data %i:%i %s{%i} \n" %(i+1,i+1,dataset['srcspectra'],intID))
            f.write("back %i %s{%i} \n" %(i+1,dataset['bkgspectra'],intID))
            if('weightedrsp' in dataset.keys()):
              f.write("resp %i %s{%i} \n" %(i+1,dataset['weightedrsp'],intID))
            else:
              f.write("resp %i %s \n" %(i+1,dataset['rspfile']))
            pass
          pass
        pass
        f.close()
      pass
      #Update the keywords in the PHA files
      for dataset in self.datasets:
        if(not datasetsFilter(dataset)):
            continue
        pass
        f                     = pyfits.open(dataset['srcspectra'])
        header                = f['SPECTRUM',1].header.copy()
        nIntervals            = len(f['SPECTRUM',1].data)
        f.close()
        
        #Get the maximum length of a line
        maxDim                = max(len(dataset['bkgspectra']),len(dataset['rspfile']))+20
        frmt                  = "%sA" % (maxDim)
        #Add two columns to the PHA II file: BACKFILE and RESPFILE
        backfileArr           = numpy.array(map(lambda x:"%s{%i}" %(dataset['bkgspectra'],x+1),range(nIntervals)))
        backfileCol           = pyfits.Column(name='BACKFILE',format=frmt,
                                       array=backfileArr)
        if 'weightedrsp' in dataset.keys():
          respfileArr         = numpy.array(map(lambda x:"%s{%i}" %(dataset['weightedrsp'],x+1),range(nIntervals)))
        else:
          respfileArr         = numpy.array(map(lambda x:"%s{%i}" %(dataset['rspfile'],x+1),range(nIntervals)))
        pass
        respfileCol           = pyfits.Column(name='RESPFILE',format=frmt,
                                              array=respfileArr)        
        #Make a fake table
        newtable       = pyfits.new_table(pyfits.ColDefs([backfileCol,respfileCol]))
        
        #Reopen the file and append the columns
        f              = pyfits.open(dataset['srcspectra'])
        
        if('RESPFILE' in f['SPECTRUM',1].data.names):
          finalTable   = pyfits.BinTableHDU(f['SPECTRUM',1].data,f['SPECTRUM',1].header)
          for i in range(len(finalTable.data)):
            finalTable.data.RESPFILE[i] = respfileArr[i]
            finalTable.data.BACKFILE[i] = backfileArr[i]
          pass
        else:
          coldef         = f['SPECTRUM',1].columns + newtable.columns
          finalTable     = pyfits.new_table(coldef,header=header)
        pass
        finalTable.header.set("POISSERR",True)
        
        #Copy also GTI and EBOUNDS
        primary        = f[0].copy()
        ebounds        = f['EBOUNDS'].copy()
        gti            = f['GTI'].copy()
        f.close()
        
        #Create the new file
        hdulist        = pyfits.HDUList([primary,finalTable,ebounds,gti])
        hdulist.writeto("%s__" %(dataset['srcspectra']))
        os.remove(dataset['srcspectra'])
        os.rename("%s__" %(dataset['srcspectra']),dataset['srcspectra'])
      pass  
    pass
    
    self.updateRootStatusbar("The scripts loadData_%s_int*.xcm have been produced." %(self.datasets[0].triggerName,),"You can use them in Xspec to load data, entering for example:\n\n XSPEC>@loadData_%s_int01.xcm\n\n at the XSPEC prompt." %(self.datasets[0].triggerName))
  pass
  
  def browseTriggers(self,window,triggerNameVar,triggerTimeVar,raVar,decVar):
     browser                  = TriggerSelector(window)
     try:
       window.wait_window(browser.root)
       triggerNameVar.set(browser.triggerName)
       triggerTimeVar.set(browser.triggerTime)
       raVar.set(browser.ra)
       decVar.set(browser.dec)
     except:
       #Problem with the download (most probably)
       return
  pass
  
  def downloadDataSet(self):
    #self.cleanUserInteractionFrame()
    thisWindow                = SubWindow(self.root,
                                          transient=True,title="Download data",
                                          initialHint="Please insert a trigger name/number, and select which data you want to download.")    
    thisWindow.bottomtext.config(state="normal")
    thisWindow.hyperlinkManager= HyperlinkManager(thisWindow.bottomtext)
    thisWindow.bottomtext.insert(END,"You can also download trigger data directly from the HEASARC clicking on these links:  ")
    thisWindow.bottomtext.insert(END,"GBM data",thisWindow.hyperlinkManager.add(lambda: self.openWebLink('http://heasarc.gsfc.nasa.gov/db-perl/W3Browse/w3table.pl?tablehead=name%3Dfermigtrig&Action=More+Options')))
    thisWindow.bottomtext.insert(END,", ")
    thisWindow.bottomtext.insert(END,"LAT LLE data",thisWindow.hyperlinkManager.add(lambda: self.openWebLink('http://heasarc.gsfc.nasa.gov/db-perl/W3Browse/w3table.pl?tablehead=name%3Dfermille&Action=More+Options')))
    thisWindow.bottomtext.insert(END,". Moreover, you can download GBM daily data ")
    thisWindow.bottomtext.insert(END,"here",thisWindow.hyperlinkManager.add(lambda: self.openWebLink('http://heasarc.gsfc.nasa.gov/db-perl/W3Browse/w3table.pl?tablehead=name%3Dfermigdays&Action=More+Options')))
    thisWindow.bottomtext.insert(END," and LAT photon data ")
    thisWindow.bottomtext.insert(END,"here",thisWindow.hyperlinkManager.add(lambda: self.openWebLink('http://fermi.gsfc.nasa.gov/cgi-bin/ssc/LAT/LATDataQuery.cgi')))
    thisWindow.bottomtext.insert(END, ".\n\n")
    thisWindow.bottomtext.image_create(END, image=self.lightbulb)
    thisWindow.bottomtext.insert(END,"Insert manually the trigger number, or click on 'Browse triggers' to download the list of all triggers from the HEASARC website and select from there.")

    thisWindow.bottomtext.config(state="disabled")
    #Create two labels and two entries
    #colWidth                  = 60
    
    #Trigger form
    triggerFrame              = Frame(thisWindow.frame)
    triggerFrame.grid(row=0,column=0)
    triggerForm               = EntryPoint(triggerFrame,
                                           labeltext="Trigger name:",
                                           helptext="Trigger number or name (Examples: 'bn100724029','SF120603745')",
                                           textwidth=20,initvalue='',
                                           directory=False,browser=False,
                                           inactive=False)
    browserButton             = Button(triggerFrame,text="Browse triggers",font=NORMALFONT,
                                       command=lambda: self.browseTriggers(thisWindow.window,triggerForm.variable,triggerTimeForm.variable,raForm.variable,decForm.variable))
    browserButton.grid(row=0,column=3)
    
    triggerTimeForm           = EntryPoint(triggerFrame,
                                           labeltext="Trigger time:",
                                           helptext="Trigger time in MET",
                                           textwidth=20,initvalue='',
                                           directory=False,browser=False,
                                           inactive=False)
    raForm                    = EntryPoint(triggerFrame,
                                           labeltext="R.A.",
                                           helptext="Right Ascension (J2000), decimal format (deg)",
                                           textwidth=20,initvalue='',
                                           directory=False,browser=False,
                                           inactive=False)
    decForm                   = EntryPoint(triggerFrame,
                                           labeltext="Dec.",
                                           helptext="Declination (J2000), decimal format (deg)",
                                           textwidth=20,initvalue='',
                                           directory=False,browser=False,
                                           inactive=False)
    #Data to download: GBM, LLE or both?
    checkButtonsFrame         = Frame(thisWindow.frame)
    checkButtonsFrame.grid(row=2,column=0)
    
    downloadGBM               = IntVar(0)
    GBMcheckbutton            = Checkbutton(checkButtonsFrame,
                                   text="Download GBM data",
                                   variable=downloadGBM)
    GBMcheckbutton.grid(row=0,column=0,sticky=W)
    
    downloadLLE               = IntVar(0)
    LLEcheckbutton            = Checkbutton(checkButtonsFrame,
                                  text="Download LLE data",
                                  variable=downloadLLE)
    LLEcheckbutton.grid(row=1,column=0,sticky=W)
    
    downloadLAT               = IntVar(0)
    LATcheckbutton            = Checkbutton(checkButtonsFrame,
                                  text="Download LAT standard data (Transient and cleaner classes)",
                                  variable=downloadLAT)
    LATcheckbutton.grid(row=2,column=0,sticky=W)
    
    buttonFrame               = Frame(thisWindow.frame)
    buttonFrame.grid(row=3,column=0)
    #Download button
    downloadButton            = Button(buttonFrame,
                                  text="Download data", font=NORMALFONT,
                                  command=lambda: self.downloadDataSetFromFTP(
                                               triggerForm.get(),
                                               triggerTimeForm.get(),
                                               raForm.get(),
                                               decForm.get(),
                                               thisWindow.window,
                                               downloadLLE.get(),
                                               downloadGBM.get(),
                                               downloadLAT.get()))
    downloadButton.grid(row=0,column=0)
    #Cancel button
    cancelButton              = Button(buttonFrame,
                                  text="Cancel", font=NORMALFONT,
                                  command=thisWindow.window.destroy)
    cancelButton.grid(row=0,column=1)
    
    #Now launch the browser
    #self.browseTriggers(thisWindow.window,triggerForm.variable,triggerTimeForm.variable,raForm.variable,decForm.variable)
  pass
  
  def downloadDataSetFromFTP(self,triggerName,triggerTime,ra,dec,thisWindow,downloadLLE,downloadGBM,downloadTransient):
    if((downloadLLE==0 and downloadGBM==0 and downloadTransient==0) or triggerName==''):
      #nothing to do!
      self.fillUserInteractionFrame()
      return
    pass
        
    if(triggerName.find("GRB")==0):
      triggerName             = triggerName[3:]
    elif(triggerName.find("SF")==0):
      triggerName             = triggerName[2:]
    elif(triggerName.find("bn")==0):
      triggerName             = triggerName[2:]
    pass
    
    downloaders               = []
    
    if(downloadTransient==1):
      LATdownloader           = downloadTransientData.DownloadTransientData(triggerName,self.configuration.get('ftpWebsite'),
                                                               self.configuration.get('dataRepository'),
                                                               parent=self.root)
      try:
        howManySeconds        = askfloat("LAT data","Please indicate how many seconds of data\nafter the trigger you would like to download:",initialvalue=10000,parent=self.root)

        LATdownloader.setCuts(ra,dec,60.0,float(triggerTime),float(triggerTime)-1000,float(triggerTime)+howManySeconds,'MET')
      except:
        showerror("Error downloading data from FTP","Could not download data for trigger %s. Reason:\n\n '%s' \n\n." %(triggerName,sys.exc_info()[1]),parent=self.root)
      else:
        downloaders.append(LATdownloader)
    
    if(downloadLLE==1):
      downloaders.append(getLLEfiles.LLEdataCollector(triggerName,self.configuration.get('ftpWebsite'),
                                                               self.configuration.get('dataRepository'),
                                                               parent=self.root))
    if(downloadGBM==1):
      #Ask the user which kind of file he/she wants to download (CSPEC,TTE,RSP and CTIME)
      gbmDataSelWindow          = SubWindow(thisWindow,transient=True,title="Select GBM data to download",
                                          initialHint="Please select which GBM data you want to download",
                                          geometry="500x200+20+20")  
      #Create two labels and two entries
      colWidth                  = 60
            
      #Data to download: GBM, LLE or both?
      checkButtonsFrame         = Frame(gbmDataSelWindow.frame,width=gbmDataSelWindow.frame.cget('width'))
      checkButtonsFrame.grid(row=0,column=0)
      
      variables                 = [IntVar(),IntVar(),IntVar(),IntVar()]
      for v in variables:
        v.set(1)
      variables[3].set(0)
      types                     = ["TTE","CSPEC","RSP","CTIME"]
      checks                    = []
      for i,v,t in zip(range(len(variables)),variables,types):
        checks.append(Checkbutton(checkButtonsFrame,text="%s data" %(t),variable=v))
        checks[-1].grid(row=i,column=0,sticky=W)
      pass
      checks[1].config(state=DISABLED)
      checks[2].config(state=DISABLED)
      #Download button
      
      def go():
        gbmDataSelWindow.window.destroy()
        downloaders.append(getGBMfiles.GBMdataCollector(triggerName,self.configuration.get('ftpWebsite'),
                                                               self.configuration.get('dataRepository'),
                                                               variables[0].get(),variables[1].get(),
                                                               variables[2].get(),variables[3].get(),
                                                               parent=self.root))
      
      goButton                  = Button(gbmDataSelWindow.frame,text="Go", font=NORMALFONT,
                                         command=go)
      goButton.grid(row=1,column=0)
      
      cancelButton              = Button(gbmDataSelWindow.frame,text="Cancel", font=NORMALFONT,
                                         command=lambda: gbmDataSelWindow.window.destroy)
      cancelButton.grid(row=1,column=1)
      thisWindow.wait_window(gbmDataSelWindow.window)      
    pass
    
    thisWindow.destroy()
    
    downloadedSomething       = False
    for downloader in downloaders:
      try:
        downloader.getFTP()
      except GtBurstException as gte:
          sys.stdout.flush()
          showerror("Error","%s" % (gte.longMessage))
          continue
      except:
        if(downloadedSomething):
          self.loadDataSetsFromAdirectory(os.path.join(self.configuration.get('dataRepository'),"bn%s" %(triggerName)))      
        pass
        self.fillUserInteractionFrame()
        raise
      finally:
        downloadedSomething     = True
    pass
    
    if(downloadedSomething):
      self.loadDataSetsFromAdirectory(os.path.join(self.configuration.get('dataRepository'),"bn%s" %(triggerName)))      
    self.fillUserInteractionFrame()
  pass
  
  def configure(self):
    configureWindow           = SubWindow(self.root,transient=True,title="Configuration",
                                          initialHint="Please fill the form, then click save.")
    configureWindow.window.geometry("800x250+20+20")
    configureWindow.bottomtext.config(state="normal")
    configureWindow.bottomtext.insert(END,"\n\n")
    configureWindow.bottomtext.image_create(END, image=self.lightbulb)
    configureWindow.bottomtext.insert(END,"If you want to restore the original configuration, simply remove the file:\n        %s\n\n" %(self.configuration.configurationFile))
    configureWindow.bottomtext.config(state="disabled")
    
    
    #Read and write a configuration file
    entries                   = {}
    sortedKeys                = sorted(self.configuration.keys())
    
    for key in self.configuration.keys():
      if(key!='maxNumberOfCPUs'):
        directory             = True
        browser               = True
      else:
        directory             = False
        browser               = False
      pass
      entries[key]            = EntryPoint(configureWindow.frame,labeltext=self.configuration.getDescription(key)+":",
                                             textwidth=40,initvalue=self.configuration.get(key),
                                             directory=directory,browser=browser)
    
    #entries['ftpWebsite']     = EntryPoint(configureWindow.frame,labeltext=self.configuration.getDescription('ftpWebsite')+":",
    #                                       textwidth=40,initvalue=self.configuration.get('ftpWebsite'))
    # 
    buttonFrame               = Frame(configureWindow.frame)
    buttonFrame.grid(columnspan=3)    
    saveButton                = Button(buttonFrame,text="Save", font=NORMALFONT,
                                 command=lambda: self.saveConfiguration(entries,configureWindow.window))
    saveButton.grid(row=0,column=0)
    cancelButton              = Button(buttonFrame,text="Cancel",font=NORMALFONT,command=configureWindow.window.destroy)
    cancelButton.grid(row=0,column=1)
  pass
  
  def saveConfiguration(self,entries,window):
    for key in entries.keys():
      self.configuration.set(key,entries[key].get())
    pass
    self.configuration.save()
    showinfo("Configuration saved!","Configuration saved! If you want to restore the default configuration\nsimply remove the file\n%s" %(self.configuration.configurationFile),parent=window)
    window.destroy()
  pass
  
  def loadDataSetsFromAdirectory(self,directory=None):
    #Load a dataset
    #Select a file from a browser and change correspondingly the given entry
    if(directory==None):
      directory                = fancyFileDialogs.chooseDirectory(self.root,
                                                title="Please select a directory containing data files",
                                                initialdir=self.configuration.get('dataRepository'))
    pass
        
    if(directory==None or directory=='' or directory==()):
      #Cancel button, do nothing
      return
    pass
    
    #Find GBM and LLE datasets in this directory
    #Find all CSPEC files
    cspecFiles                = glob.glob(os.path.join(os.path.abspath(directory),"*cspec*.pha"))
    if(len(cspecFiles)==0):
      showerror("Error","No data available in directory %s.\n" %(os.path.abspath(directory)),parent=self.root)
      return
      
    datasets                  = []
    triggers                  = []
    for cspec in cspecFiles:
      dataset,trigger,triggered = self._findOtherFiles(cspec,self.root)
      datasets.append(dataset)
      triggers.append(trigger)
      if(trigger!=triggers[-1]):
        showerror("Inconsistent data","Directory %s contains data from different triggers! Please clean it, and retry." %(directory))
        return
    pass
    
    #Sort the detectors by energy (NaIs, BGOs, LAT)
    def my_sorter(dataset):
      try:
        return knownDetectors.index(dataset.detector)
      except:
        return 9999
    datasets.sort(key=my_sorter)
    
    #Open a window
    datasetsWindow            = SubWindow(self.root,transient=True,title="Select datasets",
                                          initialHint="Select datasets to use for your analysis. Pre-selected detectors are NaIs closer than 50 deg to the source, the closest BGO and the LAT (if present).")
    #datasetsWindow.window.geometry("350x500+20+20")
    datasetsWindow.bottomtext.config(state="normal")
    datasetsWindow.bottomtext.insert(1.0,"In parenthesis you can find the angle between each detector and the source.\n\n")
    datasetsWindow.bottomtext.config(state="disabled")
    datasetsWindow.bottomtext.image_create(1.0, image=self.lightbulb)
    
    #One check button for each detector   
    detFrame                  = Frame(datasetsWindow.frame)
    detFrame.grid(row=0,column=0)
    
    #Horizontal line
    line                      = Frame(datasetsWindow.frame,height=2,bg="black",width=200)
    line.grid(row=1,column=0,sticky='NSWE')
    
    #Place a check button to use only CSPEC file (when TTE files are saturated, for example)
    useOnlyCSPEC              = IntVar()
    onlyCSPECbutton           = Checkbutton(datasetsWindow.frame,text="Do NOT use GBM TTE files (you loose time resolution!)",
                                            variable=useOnlyCSPEC,height=4,wraplength=140)
    onlyCSPECbutton.grid(row=2,column=0)
    
    line2                     = Frame(datasetsWindow.frame,height=2,bg="black",width=200)
    line2.grid(row=3,column=0,sticky='NSWE')
    
    okButton                  = Button(datasetsWindow.frame,text="Ok", font=NORMALFONT,
                                 command=lambda: self.registerDatasets(datasets,parValues,datasetsWindow.window,bool(useOnlyCSPEC.get())))
    okButton.grid(row=4,column=0)
    
    checkButtons              = []
    parValues                 = []
    
    col                        = 0
    row                        = 0
    for i,dataset in enumerate(datasets):
      #Get coordinates of the object (to compute the angle to the detector)
      try:
        RA_OBJ                = pyfits.getval(dataset['rspfile'],"RA_OBJ",extname="SPECRESP MATRIX",extver=1)
        DEC_OBJ               = pyfits.getval(dataset['rspfile'],"DEC_OBJ",extname="SPECRESP MATRIX",extver=1)
      except:
        try:
          RA_OBJ              = pyfits.getval(dataset['rspfile'],"RA_OBJ",extname="MATRIX",extver=1)
          DEC_OBJ             = pyfits.getval(dataset['rspfile'],"DEC_OBJ",extname="MATRIX",extver=1)
        except:
          #showinfo("No RA,DEC","No RA_OBJ,DEC_OBJ keywords in response file %s" %(dataset['rspfile']))
          RA_OBJ              = 'not available'
          DEC_OBJ             = 'not available'
      pass
      
      angle                   = 99999
      angleString             = 'n.a.'
      #Compute the angle between this detector and the object
      if(dataset.detector.find('LAT')>=0 and RA_OBJ!='not available'):
        RA_SCZ, DEC_SCZ, RA_SCX, DEC_SCX = dataHandling.getPointing(dataset.triggerTime,dataset['ft2file'],True)
        angle               = angularDistance.getDetectorAngle(RA_SCX,DEC_SCX,RA_SCZ,DEC_SCZ,RA_OBJ,DEC_OBJ,dataset.detector)
        angleString         = '%3.0f' %(angle)
        dataset.angleToGRB  = angle
      elif('trigdat' in dataset.keys() and RA_OBJ!='not available'):
        try:
          f                     = pyfits.open(dataset['trigdat'])
          #Get spacecraft pointing
          RA_SCX              = f[0].header['RA_SCX']
          DEC_SCX             = f[0].header['DEC_SCX']
          RA_SCZ              = f[0].header['RA_SCZ']
          DEC_SCZ             = f[0].header['DEC_SCZ']
          f.close()
          angle               = angularDistance.getDetectorAngle(RA_SCX,DEC_SCX,RA_SCZ,DEC_SCZ,RA_OBJ,DEC_OBJ,dataset.detector)
          angleString         = '%3.0f' %(angle)
          dataset.angleToGRB  = angle
        except:
          #If something goes wrong, just continue without annoying the user
          pass
        pass
      pass
            
      parValues.append(IntVar())
      if(angleString!='n.a.'):
        if(dataset.detector.find('b')==0):
          #BGO
          #get the angle for the other bgo
          if(dataset.detector=='b0'):
            other             = 'b1'
          else:
            other             = 'b0'  
          otherAngle          = angularDistance.getDetectorAngle(RA_SCX,DEC_SCX,RA_SCZ,DEC_SCZ,RA_OBJ,DEC_OBJ,other)
          if(otherAngle < angle):
            parValues[-1].set(int(0))
          else:
            parValues[-1].set(int(1))
        elif(dataset.detector.find('LAT')!=-1):
          #Always select the LAT
          parValues[-1].set(int(1))
        elif(dataset.detector.find('n')==0):
          if(angle <= 50):
            #preselect this detector
            parValues[-1].set(int(1))
          else:
            parValues[-1].set(int(0))
      else:
        parValues[-1].set(int(0))
      pass  
      checkButtons.append(Checkbutton(detFrame,text="%-5s (%s deg)  " % (dataset.detector,angleString),
                                      variable=parValues[-1]))
      checkButtons[-1].grid(row=row,column=col,sticky='W')
      if(col==1):
        col                    = 0
        row                   += 1
      else:
        col                    = 1
      pass
    pass
    datasetsWindow.frame.columnconfigure(0,weight=1,minsize=200)
    detFrame.columnconfigure(0,weight=1,minsize=50)
    detFrame.columnconfigure(1,weight=1,minsize=50)
    
  pass
  
  def registerDatasets(self,datasets,parValues,parent,useOnlyCSPEC=False):
    self.datasets             = []
    self.useOnlyCSPEC         = useOnlyCSPEC
    triggerTimes              = []
    RAs                       = []
    DECs                      = []
    names                     = []
    for dataset,yesNo in zip(datasets,map(lambda x:x.get(),parValues)):
      if(yesNo==1):
        triggerTimes.append(dataset.triggerTime)
        try:
          RAs.append(pyfits.getval(dataset['rspfile'],"RA_OBJ",extname="SPECRESP MATRIX",extver=1))
          DECs.append(pyfits.getval(dataset['rspfile'],"DEC_OBJ",extname="SPECRESP MATRIX",extver=1))
        except:
          try:
            RAs.append(pyfits.getval(dataset['rspfile'],"RA_OBJ",extname="MATRIX",extver=1))
            DECs.append(pyfits.getval(dataset['rspfile'],"DEC_OBJ",extname="MATRIX",extver=1))
          except:
            #Do not bother the user, RA and DEC are just for check, they aren't really
            #used in the program
            RAs.append(999)
            DECs.append(999)
            pass
        #Check that the dataset is complete, otherwise ask for the missing files
        if(dataset.status=="noRESP"):
          showinfo("No response for %s" %(dataset.detector),
                   "No RSP file available for detector %s! Please select one (be careful, no check will be performed)" % dataset.detector,
                   parent=parent)
          userResponse       = fancyFileDialogs.chooseFile(title="Please select RSP file for detector %s" %(dataset.detector),
                                               initialdir=self.configuration.get('dataRepository'),
                                               filetypes=[("Detector responses","*.rsp*"),("All files","*")])
          if(userResponse==None or userResponse==''):
            showerror("No rsp provided","You did not provide a RSP file, ignoring detector %s" %(dataset.detector),parent=parent)
            continue
          else:
            dataset['rspfile'] = os.path.abspath(os.path.expanduser(userResponse))                                    
        pass
        if(dataset.status=="noTTE" and useOnlyCSPEC==False):
          showinfo("No TTE file for detector %s" %(dataset.detector),"No TTE file found for detector %s, using CSPEC file (you loose time resolution)." %(dataset.detector),parent=parent)
          dataset['eventfile'] = dataset['cspecfile']
        pass
        
        self.datasets.append(dataset)
        names.append(dataset.detector)
      pass
    pass    
    parent.destroy()   
    
    #Safety checks on the loaded datasets
    
    #Check for the coordinates of the source
    if((max(RAs)-min(RAs) > 0.2) or (max(DECs)-min(DECs) > 0.2)):
      string                  = map(lambda x:"%s -> (%s,%s); " %(x[0],x[1],x[2]),zip(names,RAs,DECs))
      showerror("Inconsistent coordinates","The selected datasets have been generated with inconsistent coordinates for the source.\n%s\n Please write to the FSSC." %(string),
                parent=self.root)
      self.datasets           = []
     
    #Check that all datasets have the same trigger time, otherwise ask the user for one
    if(max(triggerTimes)==-1):
      #No trigger time information at all!
      triggerTime = askfloat("No trigger time in data","No trigger time contained in datasets. You have to manually specify the trigger time:",parent=self.root)
      if(triggerTime=='' or triggerTime==0 or triggerTime==None):
        self.datasets         = []
        return
      for dataset in datasets:
        print("Using %s as trigger time for detector %s and object %s" %(triggerTime,dataset.detector,
                                                                          dataset.triggerName))
        dataset.triggerTime = triggerTime
    if(max(triggerTimes)-min(triggerTimes) > 1E-3):
      msg                     = "Minimum trigger time: %s\nMaximum trigger time: %s" %(min(triggerTimes),max(triggerTimes))
      triggerTime = askfloat("Inconsistent trigger times","Inconsistent trigger times between datasets.\n%s\n You have to manually specify the trigger time:" %msg,parent=self.root)
      if(triggerTime=='' or triggerTime==0 or triggerTime==None):
        self.datasets         = []
        return
      for dataset in datasets:
        print("Using %s as trigger time for detector %s and trigger %s" %(triggerTime,dataset.detector,
                                                                          dataset.triggerName))
        dataset.triggerTime = triggerTime
    else:
      triggerTime           = datasets[0].triggerTime
    pass
        
    #Write the keyword UREFTIME in all the input data files, which I will use as 
    #reference time, to avoid overwriting the TRIGTIME keyword
    for dataset in datasets:
      for key in ['rspfile','cspecfile']:
        f                     = pyfits.open(dataset[key],"update")
        f[0].header.set("UREFTIME",float(triggerTime))
        f.close()
      pass
    pass  
    
    #Update the status bar in the main window
    if(len(self.datasets)>0):     
      #Update the information on the object
      self.fillObjectInfo()
      
      #If the user do not want to use TTE files, overwrite the 'eventfile' element 
      #in all GBM datasets
      if(useOnlyCSPEC):
        for dataset in self.datasets:
          if(dataset.detector.find("LAT")<0):
            dataset['eventfile'] = dataset['cspecfile']
          pass
        pass
      pass
        
      #Activate the Make spectra button in the main window if there is either a GBM or a LLE dataset
      if(len(filter(lambda x:x.detector!="LAT",self.datasets))>0):
        self.tasksmenu.entryconfig(4,state=NORMAL)
      
      #If there is a LAT dataset, activate also the likelihood and the simulations button
      if(len(filter(lambda x:x.detector=="LAT",self.datasets))>0):
        for i in range(4):
          self.tasksmenu.entryconfig(i,state=NORMAL)
      #Sort the detectors by energy (NaIs, BGOs, LAT-LLE,LAT)
      def my_sorter(dataset):
        if(dataset.detector[0]=='n'):
          return 0
        elif(dataset.detector[0]=='b'):
          return 1
        elif(dataset.detector.find("LAT-LLE")==0):
          return 2
        elif(dataset.detector.find("LAT")==0):
          return 3 
      self.datasets.sort(key=my_sorter)
      
      #Display check buttons
      if(self.displayDetFrame!=None):
        self.displayDetFrame.destroy()
      pass
      
      self.displayDetFrame         = Frame(self.userInteractionFrame)
      self.displayDetFrame.grid(column=0,sticky='NSWE')
      lab                     = Label(self.displayDetFrame,
                                      text='\n\n\nDetectors to display in the LC:',
                                      anchor=SW)
      lab.grid(column=0,row=0,columnspan=3,sticky=SW)
      
      self.displayDatasetVars = []
      self.displayCheckButtons = []
      for i,dataset in enumerate(self.datasets):
        self.displayDatasetVars.append(IntVar())
        self.displayDatasetVars[-1].set(1)
        self.displayCheckButtons.append(Checkbutton(self.displayDetFrame,
                                      text="%s (%i deg)" % (dataset.detector,dataset.angleToGRB),
                                      variable=self.displayDatasetVars[-1],
                                      command=self.makeLightCurves))
        row                   = i/3+1
        col                   = i-(row-1)*3
        
        self.displayCheckButtons[-1].grid(column=col,row=row,sticky=SW)
      pass
      self.saveUserInteractionFrame()
      self.writeDefaultHelpMessage()
      self.makeLightCurves()
    else:
      #No datasets, nothing to do
      self.updateRootStatusbar("No datasets loaded.")
      #Deactivate commands
      for i in range(5):
        self.tasksmenu.entryconfig(i,state=DISABLED)
    pass
    return
  pass
  
  def writeDefaultHelpMessage(self):
      message                 = "Loaded datasets: %s" % ','.join(map(lambda x:x.detector,self.datasets))
      if(self.useOnlyCSPEC):
        message              += " (NOT using GBM TTE data, as per user request)"
      self.updateRootStatusbar(message,"You can zoom/pan the light curve using the toolbar at the bottom of the figure. For help on the use of the toolbar, see ")
      self.bottomtext.config(state=NORMAL) 
      self.bottomtext.insert(END,"http://matplotlib.org/users/navigation_toolbar.html",self.hyperlink.add(lambda: self.openWebLink("http://matplotlib.org/users/navigation_toolbar.html")))
      self.bottomtext.config(state=DISABLED) 
  
  def makeLightCurves(self):
    self.root.update_idletasks()
    if(self.eventLock):
      #Another event is already running
      return
    else:
      self.eventLock            = True
    pass
    
    detToDisplay                = filter(lambda x:x[0].get()==1,zip(self.displayDatasetVars,self.datasets))
    detToDisplay                = map(lambda x:x[1],detToDisplay)

    nDatasets                   = len(detToDisplay)
    
    if(nDatasets==0):
      self.eventLock            = False
      return
    
    print("Making the light curve...")
    
    self.figure.clear()
    
    #Create figure
    xlabel                      = "Time since trigger"
    ylabel                      = "Counts/s"
    self.figure.subplots_adjust(left=0.15, right=0.85, top=0.95, bottom=0.1,hspace=0)
    self.subfigures             = []
    left                        = True
    for i,dataset in enumerate(detToDisplay):
      f                           = pyfits.open(dataset['cspecfile'])  
      s                           = f['SPECTRUM']
      d                           = s.data[(s.data.field('QUALITY')==0)]
      trigTime                    = dataset.triggerTime
      counts                      = d.field('COUNTS')
      met                         = d.field('TIME')-trigTime
      exposure                    = d.field('EXPOSURE')
      N                           = len(met)
      LC                          = N*[0]
      
      for j in range(N): 
        if(exposure[j]>0):
          LC[j]                     = counts[j].sum()/exposure[j]
      pass
      
      if(i==0):
        self.subfigures.append(self.figure.add_subplot(nDatasets,1,i+1))      
      else:
        self.subfigures.append(self.figure.add_subplot(nDatasets,1,i+1,
                                               sharex=self.subfigures[0],
                                                         xlabel=xlabel))        
      if(i!=nDatasets-1):
        self.subfigures[-1].xaxis.set_visible(False)
      self.subfigures[-1].step(met,LC,where='post')
      if(left):
        self.subfigures[-1].yaxis.tick_left()
        left                  = False
      else:
        self.subfigures[-1].yaxis.tick_right()
        left                  = True
      pass
      self.subfigures[-1].locator_params(tight=True, axis='y')
      self.subfigures[-1].text(0.05, 0.9,'%s' %(dataset.detector), horizontalalignment='left', verticalalignment='top',
               transform = self.subfigures[-1].transAxes)
    pass
    self.figure.text(0.05,0.5,ylabel,rotation='vertical',verticalalignment='center',horizontalalignment='left')
    self.figure.text(0.95,0.5,ylabel,rotation='vertical',verticalalignment='center',horizontalalignment='right')
    self.figure.axes[0].set_xlim([-1000,1000])
    self.canvas.draw()
    f.close()
    print("Done!")
    self.eventLock            = False
pass

def reset():
    """Restarts the current program.
    Note: this function does not return. Any cleanup action (like
    saving data) must be done before calling this function."""
    yes                        = askyesno("Reset","Do you really want to start over?")
    if(yes):
      python = sys.executable
      os.execl(python, python, * sys.argv)
    else:
      #Do nothing
      print("\nReset canceled.\n")
pass

if __name__ == '__main__':
     g = GUI()
     g.run()
