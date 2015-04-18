from Tkinter import *
from GtBurst.fontDefinitions import *
from GtBurst import commandDefiner
from GtBurst.EntryPoint import EntryPoint
import os
import traceback
from tkMessageBox import showerror, showinfo
from GtBurst.GtBurstException import GtBurstException
import dataHandling

class CommandPipeline(object):
    def __init__(self,frame,helpCallback,commands,datasets,console,
                      finalProducts,finalCallback,figure,figureFrame,canvas,**kwargs):
      self.commands           = commands
      self.datasets           = datasets
      self.console            = console
      self.finalProducts      = finalProducts
      self.finalCallback      = finalCallback
      self.figure             = figure
      self.frame              = frame
      self.figureFrame        = figureFrame
      self.canvas             = canvas
      self.helpCallback       = helpCallback
      
      #Fake filter (always return True)
      self.datasetsFilter     = lambda x: True
      
      for k,v in kwargs.iteritems():
        if(k=='datasetsfilter'):
          self.datasetsFilter  = v
        pass
      pass
      
      if(len(filter(self.datasetsFilter,self.datasets))==0):
        #Nothing to do
        showerror("No appropriate datasets loaded","You have to load at least one appropriate dataset first!")
        return
      pass  
      
      #This dictionary will contains the parameters value for all commands
      self.entries            = []
      self.frames             = []
      
      #Setup command 1
      self.currentStep        = -1
      self.setupFrames()
      self.setupButtons()
      self.showStep(+1)
    pass
    
    def setupFrames(self):
      self.frames           = []
      self.entries          = []
      for command in self.commands:
        self.frames.append(Frame(self.frame))
        thisCommandEntries    = {}
        for parname, parameter in command.definedParameters.iteritems():
          #Skip all parameters related to dataset files (no need to ask them again!)
          #and skip the outfile parameter (will use default values)
          if(parameter.type==commandDefiner.DATASETFILE or 
             parameter.type==commandDefiner.OUTPUTFILE or 
             parameter.type==commandDefiner.INPUTFILE or
             parname=="clobber" or 
             parname=="verbose" or
             parname=="figure" or
             parname=="tkwindow"):
            continue
          pass
          if(parameter.possibleValues!=[]):
            #Combo box
            thisCommandEntries[parname]  = EntryPoint(self.frames[-1],
                                                    labeltext=parameter.parname,
                                                    helptext=parameter.description,
                                                    possiblevalues=parameter.possibleValues)
          else:
            if(parameter.type==commandDefiner.GENERICFILE):
              thisCommandEntries[parname]  = EntryPoint(self.frames[-1],
                                                    labeltext=parameter.parname,
                                                    helptext=parameter.description,
                                                    initvalue=parameter.getValue(),
                                                    browser=True,
                                                    extension=parameter.extension)
            else:
              thisCommandEntries[parname]  = EntryPoint(self.frames[-1],
                                                    labeltext=parameter.parname,
                                                    helptext=parameter.description,
                                                    initvalue=parameter.getValue())
          if(parameter.type==commandDefiner.HIDDEN):
            thisCommandEntries[parname].subFrame.grid_forget()
            try:
              thisCommandEntries[parname].helpButton.grid_forget()
            except:
              pass
            try:
              thisCommandEntries[parname].browserButton.grid_forget()
            except:
              pass
        pass
        self.entries.append(thisCommandEntries)
        if(len(thisCommandEntries)==0):
          #No parameters for this command
          self.labelForEmptyCommands    = Label(self.frames[-1],font=LABELFONT)
          self.labelForEmptyCommands['text']      = "\nNo parameters needed for this command.\nJust click Run.\n"
          self.labelForEmptyCommands.grid(row=0,column=0,sticky=N+S+E+W)
        pass
      pass
    pass
    
    def setupButtons(self):
      self.buttonFrame        = Frame(self.frame)
      #Add the "Previous" and Next button
      self.previousButton     = Button(self.buttonFrame,
                                    text="<- Prev.",
                                    command=lambda :self.showStep(-1),
                                    font=NORMALFONT)
      self.previousButton.pack(side=LEFT,fill=X,expand=1)
      
      self.advancement        = StringVar()
      self.advancement.set("%s/%s" %(self.currentStep+1,len(self.commands)))
      dumbButton              = Label(self.buttonFrame,
                                   textvariable=self.advancement,
                                   font=NORMALFONT)
      dumbButton.pack(side=LEFT,fill=X,expand=1)
      
      goButton                = Button(self.buttonFrame,
                                    text="Run",
                                    command=self.runCommand,
                                    font=NORMALFONT)
      goButton.pack(side=LEFT,fill=X,expand=1)
      
      
      self.nextButton         = Button(self.buttonFrame,
                                    text='Next ->',
                                    command=self.showStep,
                                    font=NORMALFONT)
      self.nextButton.configure(state=DISABLED)
      self.nextButton.pack(side=LEFT,fill=X,expand=1)
      
      self.cancelButton         = Button(self.buttonFrame,
                                    text="Cancel",
                                    command=self.cleanUp,
                                    font=NORMALFONT)
      self.cancelButton.pack(side=LEFT,fill=X,expand=1)
    pass
    
    def disableButtons(self):
      for child in self.buttonFrame.pack_slaves():
        child.config(state=DISABLED)
      pass  
    pass
    
    def enableButtons(self,success=True):
      for child in self.buttonFrame.pack_slaves():
        child.config(state=NORMAL)
      pass
      if(not success):
        #Disable the Next button
        self.nextButton.configure(state=DISABLED)
      if(self.currentStep==0):
        self.previousButton.config(state=DISABLED)
    pass
        
    def showStep(self,incr=1):
      if(self.currentStep!=-1):
        #Hide the previous step
        self.frames[self.currentStep].grid_forget()
        self.buttonFrame.grid_forget()
        self.nextButton.config(state=DISABLED)  
      pass
      
      #Increment the step counter (first step is currentStep==0)
      self.currentStep       += incr
      
      if(self.currentStep > len(self.commands)-1):
        #Went after the last step... close everything
        self.cleanUp()
        
        if(self.finalProducts!=None):
          #Print a message with the produced files
          message             = "Files produced:\n"
          for dataset in self.datasets:
            if(not self.datasetsFilter(dataset)):
              continue
            message          += "\n\n-Dataset %s:" %(dataset.detector)
            for descr,product in self.finalProducts.iteritems():
              message        += "\n  %-20s : %s" %(descr,os.path.basename(dataset[product]))
            pass
          pass
          print(message)
        pass
        
        return
      pass
      
      #If we are in the first step, disable the "previous" button
      if(self.currentStep==0):
        #Disable the Previous button
        self.previousButton.config(state=DISABLED)
      else:
        if(self.currentStep==len(self.commands)-1):
          #Last step, change from "next" to "finish"
          self.nextButton['text'] = "Finish!"
        else:
          self.nextButton['text'] = "Next ->"
        self.previousButton.config(state=NORMAL)
      pass
      
      #Show frames relative to this step, and the buttons
      #self.frames[self.currentStep].pack(side=TOP,fill=X,expand=True)
      self.frames[self.currentStep].grid(column=0,row=0,sticky=N+S+E+W)
      self.advancement.set("%s/%s" %(self.currentStep+1,len(self.commands)))
      self.buttonFrame.grid(column=0,row=1,rowspan=3,sticky=N+S+E+W)
      #self.buttonFrame.pack(side=BOTTOM,fill=X,expand=True)
      self.updateHelpText()
      self.updateParameters()
      
      #If there is an active eventDisplay, clear its bindings (otherwise it will slow down everything)
      for i,ds in enumerate(self.datasets):
        if('eventDisplay' in ds.keys() and self.datasets[i]['eventDisplay']!=None):
            #Explicity free the bindinds in the eventDisplay (otherwise they will still be called)
            self.datasets[i]['eventDisplay'].unbind()
        pass
      pass
      self.figure.clear()
      self.canvas.draw()
    pass
    
    def updateParameters(self):
      #This method update the value of the form with the data stored in the datasets
      command               = self.commands[self.currentStep]
      dataset               = self.datasets[0]
      for parname, parameter in command.definedParameters.iteritems():
         if(parname in dataset.keys()):
              try:
                print("%s -> %s" %(parname,dataset[parname]))
                self.entries[self.currentStep][parname].set(dataset[parname])
              except:
                pass
    pass
    
    def cleanUp(self):
      for frame in self.frames:
        for child in frame.pack_slaves():
          child.pack_forget()
          child.destroy()
        pass
        frame.pack_forget()
        frame.destroy()
      pass
      
      self.buttonFrame.pack_forget()
      self.buttonFrame.destroy()
      
      for entry in self.entries:
        for k,v in entry.iteritems():
          v.destroy()
        pass    
      pass
      self.finalCallback(self.datasetsFilter)
    pass
    
    def updateHelpText(self):
      self.helpCallback(self.commands[self.currentStep].GUIdescription)
    pass
    
    def runCommand(self):                
            
      self.figureFrame.focus_set()
      command               = self.commands[self.currentStep]
      if(self.console==None):  
        self.console        = Console(self.windows[self.currentStep].window)
      pass
      
      thisFilter            = self.datasetsFilter
      if("dataset to use" in command.definedParameters.keys()):
        detectorToUse       = self.entries[self.currentStep]["dataset to use"].get().lower()
        thisFilter          = lambda x:x.detector.lower()==detectorToUse.lower()
      pass
      
      print("\n ==================== %s =============================== \n" %(command.name))
      
      #For each dataset, build the command line and run the command
      nProcessed            = 0
      for i,dataset in enumerate(self.datasets):
        if(not thisFilter(dataset)):
          #This detector must not be processed
          continue
        pass
        
        thisParameters      = {}
        
        for parname, parameter in command.definedParameters.iteritems():
          if(parameter.type==commandDefiner.OUTPUTFILE and (parname not in dataset.keys())):
          
            #Set up the default name
            outfileParName  = parname
            defaultName     = os.path.abspath("./%s_%s_%s.%s" %(dataset.triggerName,dataset.detector,parname,parameter.extension))
            thisParameters[outfileParName] = defaultName
          
          elif(parname=="clobber" or parname=="verbose"):
            continue
          elif(parname=="figure"):
            thisParameters[parname] = self.figure
          elif(parname=="tkwindow"):
            continue  
          else:            
            #Check if this parameter is part of the dataset
            if(parname in dataset.keys()):
              thisParameters[parname] = dataset[parname]
            if(parameter.parname in self.entries[self.currentStep].keys()):
              #Set the parameter to the user-supplied value
              userProvidedValue       = self.entries[self.currentStep][parname].get()
              if(parameter.isMandatory and userProvidedValue==''):
                showerror("Error!","You have to provide parameter %s! You did not specified a mandatory parameter, please retry." %(parname))
                return
              else:  
                thisParameters[parname] = userProvidedValue
            pass 
          pass
        pass
        
        print("\n- Running %s on dataset %s with this parameters:\n" %(command.name, dataset.detector))
        for key, value in thisParameters.iteritems():
          if(key=="figure" or key=="tkwindow"):
            continue
          print("%-20s = %s" %(key,value))
        print("")
        #Inhibits the user to press Cancel (which would leave the command
        #in a unsafe status)  
        self.disableButtons()
        success               = False
        try:
          outtuple = command.run(**thisParameters)
          if(outtuple==None):
            success         = False
          else:
            success         = True
        except commandDefiner.UserError as ue:
          showerror("Error","%s\n Please retry." %(ue.message))
          outtuple          = None
          success           = False
        except GtBurstException as error:
          showerror("Problem","Problem executing %s:\n\n '%s' \n" %(command.name,error.longMessage))
          print(error.longMessage)            
          outtuple          = None
          self.figure.clear()
          self.canvas.draw()
          success           = False
        except:            
          print map(lambda x:x[0],traceback.extract_stack())
          filename, line, dummy, dummy = traceback.extract_stack().pop()
          
          filename                     = os.path.basename( filename )
                
          msg                          = ("Snap! An unhandled exception has occurred at line %s of file %s.\n\n" %(line,filename) +
                                        "The GUI will try to continue running. Check the parameters for the task which crashed.\n\n" +
                                        " If you think this is a bug, send a message" +
                                        " to fermihelp@milkyway.gsfc.nasa.gov attaching your gtburst.log file.\n\n"+
                                        "The full traceback has been saved to the log and printed in the console.")
          showerror("Unhandled exception",msg)
          
          dataHandling.exceptionPrinter(msg,traceback.format_exc(None))
          outtuple          = None
          self.figure.clear()
          self.canvas.draw()
          success           = False
        pass
                        
        self.enableButtons(success)
        if(outtuple==None):
          #abort
          return
        #Register the output
        for key,value in zip(outtuple[0::2],outtuple[1::2]):
          self.datasets[i][key]   = value
        pass
        nProcessed           += 1
      pass
      
      #Now if we processed just one dataset, duplicate the output for
      #all the others
      if(nProcessed==1):
        for i,dataset in enumerate(self.datasets):
          if(not self.datasetsFilter(dataset)):
            #This detector must not be processed
            continue
          pass
          #No need to run again, just register the same file in all datafiles
          for key,value in zip(outtuple[0::2],outtuple[1::2]):
            self.datasets[i][key]   = value
        pass
      pass
            
      print("\n =========================================================== \n")
      self.nextButton.config(state=NORMAL)
      #self.showStep(+1)
pass
    
##################    
