import os
from Tkinter import *
from GtBurst.fontDefinitions import *
from tkMessageBox import showerror, showinfo 
#from tkFileDialog import askdirectory
#from tkFileDialog import askopenfilename
import fancyFileDialogs


def selectFile(parent,entry, extension="*",**kwargs):
    
    directory         = False
    workdir           = os.getcwd()
    for key in kwargs.keys():
      if    key.lower()=="directory":           directory    = bool(kwargs[key])
      elif  key.lower()=="workdir":             workdir      = kwargs[key]
    pass
    
    prevValue         = entry.get()
    #Select a file from a browser and change correspondingly the given entry
    if(directory):
      filename        = fancyFileDialogs.chooseDirectory(parent,title="Please select a file", initialdir=workdir)
    else:  
      filename        = fancyFileDialogs.chooseFile(parent,title="Please select a file", 
                                        filetypes=[("Default type","*.%s" %(extension)),("allfiles","*")],
                                        initialdir=workdir)
    pass
    
    if(filename!=None and filename!=()):
      entry.delete(0,END)
      entry.insert(0,"%s" % filename)
    else:
      entry.delete(0,END)
      entry.insert(0,"%s" % prevValue)
    pass
pass


class EntryPoint(object):
    def __init__(self,parent,**kwargs):      
      labelText               = ''
      browser                 = False
      directory               = False
      textWidth               = 15
      initValue               = ''
      helpText                = ''
      inactive                = False
      workdir                 = os.getcwd()
      possibleValues          = []
      extension               = '*'
      for key in kwargs.keys():
        if    key.lower()=="labeltext":         labelText      = kwargs[key]
        elif  key.lower()=="browser":           browser        = bool(kwargs[key])
        elif  key.lower()=="textwidth":         textWidth      = int(kwargs[key])
        elif  key.lower()=="initvalue":         initValue      = kwargs[key]
        elif  key.lower()=="directory":         directory      = bool(kwargs[key])
        elif  key.lower()=="workdir":           workdir        = kwargs[key]
        elif  key.lower()=="inactive":          inactive       = bool(kwargs[key])
        elif  key.lower()=="helptext":          helpText       = kwargs[key]
        elif  key.lower()=="possiblevalues":    possibleValues = kwargs[key]
        elif  key.lower()=="extension":         extension      = kwargs[key]
      pass
      self.parent             = parent
      self.parentWidth        = self.parent.cget('width') 
      
      #Get the number of rows already in use in the parent
      rows                    = len(self.parent.grid_slaves(column=0))
      #self.parent.grid_rowconfigure(rows,weight=1)
      #self.parent.grid_columnconfigure(0,weight=1)
      self.subFrame           = Frame(self.parent)
      self.subFrame.grid(row=rows,column=0,sticky=N+S+W+E)
      
      #Label
      self.label              = Label(self.subFrame,font=LABELFONT,width=textWidth)
      self.label['text']      = labelText
      self.label.grid(row=0,column=0,sticky='W')
      
      #Variable
      self.variable           = StringVar()
      
      if(possibleValues==[]):
        #Entry
        self.entry              = Entry(self.subFrame,
                                        textvariable=self.variable,
                                        font=NORMALFONT,width=textWidth)
        self.entry.grid(row=0,column=1,sticky=W)
        self.variable.set(initValue)
      else:
        #Multiple choice
        self.possibleValues = possibleValues
        self.entry         =  apply(OptionMenu, (self.subFrame, 
                                       self.variable) + tuple(self.possibleValues))
        self.entry.grid(row=0,column=1,sticky=W)
        if(initValue in possibleValues):
          self.variable.set(initValue)
        else:
          self.variable.set(possibleValues[0])
      pass
        
      if(inactive):
        self.entry.config(state='readonly')
      pass
      
      col                     = 1
      if(browser):
        self.browserButton    = Button(self.parent,text="Browse",font=NORMALFONT,
                                 command=lambda directory=directory: selectFile(self.parent,self.entry,extension,directory=directory,workdir=workdir))
        self.browserButton.grid(row=rows,column=col,sticky=E)
        col                  += 1
      if(helpText!=''):
        self.helpButton       = Button(self.parent,text="?",font=NORMALFONT,
                                  command=lambda :showinfo("Help",helpText))
        self.helpButton.grid(row=rows,column=col,sticky=E)
      pass
      self.parent.update_idletasks()
    pass
    
    def destroy(self):
      self.entry.destroy()
      self.label.destroy()
      #self.subFrame.destroy()      
      try:
        self.helpButton.destroy()
      except:
        pass
      try:
        self.browserButton.destroy()
      except:
        pass
      pass        
    pass
    
    def get(self):
      return self.variable.get()
    pass  
    
    def set(self,value):
      self.variable.set(value)
    pass
pass
