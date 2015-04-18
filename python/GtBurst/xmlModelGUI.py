from Tkinter import *
import tkFont
import tkMessageBox 
import ttk
from GtBurst.EntryPoint import EntryPoint
from GtBurst.SubWindow import SubWindow
from GtBurst.fontDefinitions import *
import os, shutil
from tkSimpleDialog import askfloat
from xml.dom.minidom import parse, parseString
import os
from collections import OrderedDict
 
class parseXML(object):
  def __init__(self,xmlFile):
    self.xmlFile              = xmlFile
    self.dom                  = parse(xmlFile)
    self.fill()
  pass
    
  def fill(self):
    self.parameters           = []
    self.doms                 = []
    for par in self.dom.getElementsByTagName("parameter"):
      self.doms.append(par)
      thisParameter           = OrderedDict()
      thisParameter['Source Name']          = self._getAttribute(par.parentNode.parentNode,'name')
      thisParameter['Name']                 = self._getAttribute(par,'name')
      try:
        value                               = "%.5g" % float(self._getAttribute(par,'value'))
      except:
        value                               = ''
      thisParameter['Value']                = value
      try:
        error                               = "%.5g" % float(self._getAttribute(par,'error'))
      except:
        error                               = ''
      thisParameter['Error']                = error
      thisParameter['Min']                  = self._getAttribute(par,'min')
      thisParameter['Max']                  = self._getAttribute(par,'max')
      thisParameter['Scale']                = self._getAttribute(par,'scale')
      thisParameter['Free']                 = self._getAttribute(par,'free')
      thisParameter['Source Type']          = self._getAttribute(par.parentNode.parentNode,'type')
      thisParameter['Feature']              = par.parentNode.localName #either Spectrum or SpatialModel
      thisParameter['Feature Type']         = self._getAttribute(par.parentNode,'type')
      thisParameter['Feature File']         = self._getAttribute(par.parentNode,'file')
      if(thisParameter['Feature File']!=''):
        thisParameter['Feature File']       = "[..]/%s" % os.path.basename(thisParameter['Feature File'])
      pass

      self.parameters.append(thisParameter)
  pass
  
  def _getAttribute(self,element,key):
    try:
      value                   = element.attributes[key].value
    except:
      value                   = ""
    return value
  pass
  
  def setAttribute(self,parameter,attributeName,newValue):
    #Find the right parameter to change
    par                       = filter(lambda x:x['Source Name']==parameter[0] and
                                                x['Source Type']==parameter[8] and
                                                x['Feature']==parameter[9] and
                                                x['Feature Type']==parameter[10] and
                                                x['Name']==parameter[1],self.parameters)[0]
    parID                     = self.parameters.index(par)
    self.doms[parID].setAttribute(attributeName.lower(),newValue)
    self.fill()
  pass
  
  def save(self):
    f                         = open(self.xmlFile,"w+")
    self.dom.writexml(f)
    f.close()
pass

def sortby(tree, col, descending):
    """Sort tree contents when a column is clicked on."""
    # grab values to sort
    data = [(tree.set(child, col), child) for child in tree.get_children('')]

    # reorder data
    data.sort(reverse=descending)
    for indx, item in enumerate(data):
        tree.move(item[1], '', indx)

    # switch the heading so that it will sort in the opposite direction
    tree.heading(col,
        command=lambda col=col: sortby(tree, col, int(not descending)))

class xmlModelGUI(object):
    def __init__(self,xmlModelFile,parent=None):
        if(parent==None):
          self.root = Tk()
          self.root.maxsize(1024,768)
          self.root.wm_title("Likelihood model %s" %(os.path.basename(xmlModelFile)))
          self.root.wm_iconname("Likelihood model")
        else:
          self.root             = Toplevel(parent)
          #self.window.geometry(geometry)
          self.root.transient(parent)
          try:
            self.root.grab_set()
          except:
            pass
        #Make a copy of the xml, which will be modified, and it will be copied back
        #overwritting the input file only at the very end
        self.workingCopy = "__xmlTempModel.xml"
        shutil.copyfile(xmlModelFile,self.workingCopy)
        self.xmlModel = parseXML(self.workingCopy)
        self.xmlModelFile = xmlModelFile
        self.columns = self.xmlModel.parameters[0].keys()
        self.tree = None
        self._setup_widgets()
        self.notSaved = False
        #Center the window
        self.root.update_idletasks()
        xp = (self.root.winfo_screenwidth() / 2) - (self.root.winfo_width() / 2)
        yp = (self.root.winfo_screenheight() / 2) - (self.root.winfo_height() / 2)
        self.root.geometry('{0}x{1}+{2}+{3}'.format(min(self.root.winfo_width(),800), self.root.winfo_height(),
                                                                        xp, yp))
        self.root.protocol("WM_DELETE_WINDOW", self.done)
        self.root.mainloop()

    def _setup_widgets(self):
        msg = ttk.Label(self.root,wraplength="4i", justify="left", anchor="n",
            padding=(5, 2, 10, 5),
            text=("Double click on a parameter to change it."))
        msg.grid(column=0,row=0)
        self.root.grid_columnconfigure(0, weight=10)
        self.root.grid_rowconfigure(0, weight=10)
        
        self.container = ttk.Frame(self.root)
        self.container.grid(column=0,row=1,sticky='nswe')

        self._setup_tree()
        self.buttonFrame = ttk.Frame(self.root)
        self.buttonFrame.grid(column=0,row=2)
        self.button = Button(self.buttonFrame,text="Done",command=self.done,height=1)
        self.button.grid(column=0,row=0)
        self.button2 = Button(self.buttonFrame,text="Save",command=self.save,height=1)
        self.button2.grid(column=1,row=0)   
    pass
    
    def done(self):
      if(self.notSaved):
        if tkMessageBox.askyesno("WARNING!", "You have modified the template but you did not save. Do you really want to exit loosing your changes?"):
          self.root.quit()
          self.root.destroy()
          try:
            os.remove(self.workingCopy)
          except:
            pass
          return
        else:
          return
        pass
      pass
      self.root.quit()
      self.root.destroy()
      try:
        os.remove(self.workingCopy)
      except:
        pass
    pass
    
    def save(self):
      #Copy back the working copy on the input file
      shutil.copyfile(self.workingCopy,self.xmlModelFile)
      self.notSaved = False
      tkMessageBox.showinfo("saved!","Likelihood model saved!")
    pass
    
    def _setup_tree(self):
        if(self.tree!=None):
          self.tree.destroy()
        # XXX Sounds like a good support class would be one for constructing
        #     a treeview with scrollbars.
        self.tree = ttk.Treeview(self.container,columns=self.columns, show="headings",
                                 selectmode='browse')
        vsb = ttk.Scrollbar(self.container,orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(self.container,orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(column=0, row=0, sticky='nsew', in_=self.container)
        vsb.grid(column=1, row=0, sticky='ns', in_=self.container)
        hsb.grid(column=0, row=1, sticky='ew', in_=self.container)

        self.container.grid_columnconfigure(0, weight=10)
        self.container.grid_rowconfigure(0, weight=10)

        self.data = self.xmlModel.parameters
        for col in self.columns:
            self.tree.heading(col, text=col.title(),
                command=lambda c=col: sortby(self.tree, c, 0))
            # XXX tkFont.Font().measure expected args are incorrect according
            #     to the Tk docs
            self.tree.column(col, width=tkFont.Font().measure(col.title()),stretch=False,minwidth=10)
        self.items = []    
        for item in self.data:
            self.items.append(self.tree.insert('', 'end', values=item.values()))

            # adjust columns lenghts if necessary
            for indx, val in enumerate(item.values()):
                ilen = tkFont.Font().measure(val)
                if self.tree.column(self.columns[indx], width=None) < ilen:
                    self.tree.column(self.columns[indx], width=ilen)
        self.tree.bind("<Double-1>", self.OnDoubleClick)
    pass
    
    def _updateParameter(self,window,par,value,mininmum,maximum,scale,free):
        pars                  = {'value':value,
                                 'min': mininmum,
                                 'max': maximum,
                                 'scale': scale,
                                 'free': free}
        for k,v in pars.iteritems():
          v                   = str(v)
          if(v=='no'):
            v                 = '0'
          elif(v=='yes'):
            v                 = '1'
          pass
          self.xmlModel.setAttribute(par,k,v)
          self.xmlModel.save()
        pass
        #Close the window
        window.destroy()
        
        #Reflect the change in the GUI
        self._setup_tree()
        self.notSaved = True
        
    pass
    
    def OnDoubleClick(self,event):
        item = self.tree.selection()[0]
        par  = self.tree.item(item,"values")

        thisWindow                = SubWindow(self.root,
                                              transient=True,title="%s" %(par[1]),
                                              initialHint="Modify the parameter %s, then click on Ok." % par[1])
        
        #Trigger form
        frame                     = Frame(thisWindow.frame)
        frame.grid(row=0,column=0)
        valueForm                 = EntryPoint(frame,
                                               labeltext="Value",
                                               helptext="Set the new starting value",
                                               textwidth=20,initvalue=par[2],
                                               directory=False,browser=False,
                                               inactive=False)
        minForm                   = EntryPoint(frame,
                                               labeltext="Minimum",
                                               helptext="Set the new minimum value",
                                               textwidth=20,initvalue=par[4],
                                               directory=False,browser=False,
                                               inactive=False)
        maxForm                   = EntryPoint(frame,
                                               labeltext="Maximum",
                                               helptext="Set the new minimum value",
                                               textwidth=20,initvalue=par[5],
                                               directory=False,browser=False,
                                               inactive=False)

        scaleForm                 = EntryPoint(frame,
                                               labeltext="Scale",
                                               helptext="Set the new scale for the parameter",
                                               textwidth=20,initvalue=par[6],
                                               directory=False,browser=False,
                                               inactive=False)       
        
        freeForm                  = EntryPoint(frame,
                                               labeltext="Free to vary",
                                               helptext="Set wheter the parameter is free to vary or fixed during the fit",
                                               textwidth=20,initvalue=par[7],
                                               directory=False,browser=False,
                                               inactive=False,possibleValues=['yes','no']) 
        
        buttonFrame               = Frame(thisWindow.frame)
        buttonFrame.grid(row=1,column=0)
        
        #ok button
        okButton                  = Button(buttonFrame,
                                           text="Ok", font=NORMALFONT,
                                  command=lambda: self._updateParameter(thisWindow.window,par,valueForm.get(),
                                           minForm.get(),maxForm.get(),scaleForm.get(),
                                           freeForm.get()))
        okButton.grid(row=0,column=0)
        #Cancel button
        cancelButton              = Button(buttonFrame,
                                           text="Cancel", font=NORMALFONT,
                                           command=thisWindow.window.destroy)
        cancelButton.grid(row=0,column=1)
    pass  
        
def main():
    root = Tk()
    root.maxsize(1024,768)
    xmlModelFile = "100724029_model_LIKE_MY_0.000_300.000.xml"
    root.wm_title("Likelihood model %s" %(os.path.basename(xmlModelFile)))
    root.wm_iconname("Likelihood model")
    app = xmlModelGUI(xmlModelFile,root)
    root.mainloop()

if __name__ == "__main__":
    main()
