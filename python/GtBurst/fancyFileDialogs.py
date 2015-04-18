import Tkinter

def init():
  root = Tkinter.Tk()
  path = '/home/giacomov/develop/pyBurstAnalysisGUI/python/GtBurst/tcl_extensions/msgcat'
  root.tk.eval("set auto_path [linsert $auto_path 0 %s]" %(path))
  path = '/home/giacomov/develop/pyBurstAnalysisGUI/python/GtBurst/tcl_extensions/fsdialog'
  root.tk.eval("set auto_path [linsert $auto_path 0 %s]" %(path))
  return root
    
#root.tk.eval("package require tile")
#root.tk.eval("tile::setTheme clam")
#root.tk.eval("set t [ttk::chooseDirectory -initialdir %s -mustexist 1]" % ('/home/giacomov/FermiData'))
#root.tk.eval("puts $t")

def _tupleToTclList(value):
  
  if(not isinstance(value,(list,tuple))):
    return value
  
  v = []
  for val in value:
    if isinstance(val, basestring):
      v.append(unicode(val) if val else '{}')
    else:
      v.append(str(val))
    pass
  pass
  return ("%s" % ' '.join('{%s}' % val for val in v))
  
def _fromPythonToTcl(optdict):
    """Formats optdict to a tuple to pass it to tcl.

    E.g. (script=False):
      {'foreground': 'blue', 'padding': [1, 2, 3, 4]} returns:
      ('-foreground', 'blue', '-padding', '1 2 3 4')"""

    opts = []
    for opt, value in optdict.iteritems():
      format = "%s"
      if isinstance(value, (list, tuple)):
        format = '{%s}'
        v = []
        for val in value:
          if isinstance(val, basestring):
            v.append(unicode(val) if val else '{}')
          else:
            v.append(str(_tupleToTclList(val)))
          pass
        pass
        
        value = format % ' '.join(('{%s}' if ' ' in val else '%s') % val for val in v)
      pass
      opts.append(("-%s" % opt, "{%s}" % value))
    pass
    
    # Remember: _flatten skips over None
    return " ".join(Tkinter._flatten(opts))


class FileDialog(object):
  def __init__(self,master=None,**kwargs):
    if(master==None):
      self.root               = Tkinter.Tk()
    else:
      self.root               = master
    pass
    self.options              = _fromPythonToTcl(kwargs)
  pass
  
  def get(self):
    #load packages
    self.root.tk.eval("set dir [ttk::getOpenFile %s]" % (self.options))
    return self.root.tk.eval("return $dir")
  pass
pass

class DirectoryDialog(object):
  def __init__(self,master=None,**kwargs):
    if(master==None):
      self.root               = Tkinter.Tk()
    else:
      self.root               = master
    pass
    
    self.options              = _fromPythonToTcl(kwargs)
  pass
  
  def get(self):
    #load packages
    tclCommand                = "set dir [ttk::chooseDirectory %s -mustexist 1]" %(self.options)
    self.root.tk.eval(tclCommand)
    return self.root.tk.eval("return $dir")
  pass
pass
  

#Utility functions

def chooseFile(*args,**kwargs):
  dialog                      = FileDialog(*args,**kwargs)
  return dialog.get()
pass

def chooseDirectory(*args,**kwargs):
  dialog                      = DirectoryDialog(*args,**kwargs)
  return dialog.get()
pass
