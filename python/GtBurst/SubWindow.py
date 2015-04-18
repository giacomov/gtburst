from Tkinter import *
from GtBurst.fontDefinitions import *

class SubWindow(object):
    def __init__(self,parent,**kwargs):
      
      title                   = ''
      transient               = True
      initialHint             = ''
      geometry                = "800x400+10+10"
      for key in kwargs.keys():
        if    key.lower()=="title":             title          = kwargs[key]
        elif  key.lower()=="transient":         transient      = bool(kwargs[key])
        elif  key.lower()=="initialhint":       initialHint    = kwargs[key]
        elif  key.lower()=="geometry":          geometry       = kwargs[key]
      pass
      
      if(transient):
        self.window             = Toplevel(parent)
        #self.window.geometry(geometry)
        self.window.transient(parent)
        try:
          self.window.grab_set()
        except:
          pass
        #parent.wait_window(self.window)
      else:
        self.window             = Toplevel(parent)
        self.window.geometry(geometry)
      pass
      
      self.window.title(title)
      
      self.frame              = Frame(self.window) #,width=geometry.split("x")[0])
      self.frame.grid(row=0,column=0)
            
      #Define a minimal menu      
      self.menubar            = Menu(self.window)
      self.filemenu           = Menu(self.menubar, tearoff=0)
      self.filemenu.add_command(label="Close", command=self.window.destroy)
      self.menubar.add_cascade(label="File",menu=self.filemenu)    
      self.window.config(menu=self.menubar)
            
      self.bottomtext         = Text(self.window, wrap='word', width=40,font=COMMENTFONT,height=10)
      self.bottomtext.mark_set("beginning", INSERT)
      self.bottomtext.insert("beginning",initialHint)
      self.bottomtext.config(state='disabled')
      self.bottomtext.grid(row=1,column=0,sticky=W+E+N+S)
      self.window.columnconfigure(0,weight=1,minsize=200)
    pass
pass
