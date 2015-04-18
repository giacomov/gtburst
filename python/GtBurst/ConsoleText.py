#Utility to redirect the output to a text widget
#(from http://stackoverflow.com/)
#Modified by G.Vianello (giacomov@slac.stanford.edu)
import subprocess
import sys
import threading
import re
from Tkinter import *
from time import localtime, strftime
import getpass
from GtBurst.HyperlinkManager import HyperlinkManager
import webbrowser

class IORedirector(object):
    '''A general class for redirecting I/O to this Text widget.'''
    def __init__(self,text_area):
        self.text_area = text_area
    def flush(self):
        #Nothing to do really
        pass

class StdoutRedirector(IORedirector):
    '''A class for redirecting stdout to this Text widget.'''
    def write(self,str):
        self.text_area.write(str,False)

class StderrRedirector(IORedirector):
    '''A class for redirecting stderr to this Text widget.'''
    def write(self,str):
        self.text_area.write(str,True)
            
class ConsoleText(Text):
    '''A Tkinter Text widget that provides a scrolling display of console
    stderr and stdout.'''
    
    def __init__(self, master=None, cnf={}, **kw):
        '''See the __init__ for Tkinter.Text for most of this stuff.'''

        Text.__init__(self, master, cnf, **kw)
        
        self.master = master
        self.started = False
        self.write_lock = threading.Lock()
        self.prevContent = ''
        
        self.tag_configure('STDOUT',background='white',foreground='black')
        self.tag_configure('STDERR',background='white',foreground='red')

        self.config(state=NORMAL)
        self.hyperlink = HyperlinkManager(self)
        self.urlpattern = re.compile("http\:[^\s^\)]+")
    
    def set_focus(self, event):
        self.focus_set()
    
    def start(self):

        if self.started:
            return

        self.started = True
        self.logfile = open("gtburst.log",'w+')
        ltime = strftime("%Y-%m-%d %H:%M:%S", localtime())
        username = getpass.getuser()
        self.logfile.write("Analysis started at %s by user %s\n\n" %(ltime,username))
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr

        stdout_redirector = StdoutRedirector(self)
        stderr_redirector = StderrRedirector(self)

        sys.stdout = stdout_redirector
        sys.stderr = stderr_redirector

    def stop(self):

        if not self.started:
            return

        self.started = False
        ltime = strftime("%Y-%m-%d %H:%M:%S", localtime())
        self.logfile.write("\n\nAnalysis ended at %s\n" %(ltime))
        self.logfile.close()
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr
    
    
    
    def write(self,val,is_stderr=False):
        #Fun Fact:  The way Tkinter Text objects work is that if they're disabled,
        #you can't write into them AT ALL (via the GUI or programatically).  Since we want them
        #disabled for the user, we have to set them to NORMAL (a.k.a. ENABLED), write to them,
        #then set their state back to DISABLED.
        val                   = str(val.encode('utf-8'))
        if(val.find("Info in <Minuit2>")>=0 or (self.prevContent=="MINUIT" and val.replace("\n","")=='')):
          #This is to avoid the many warnings from Minuit 2
          self.prevContent    = "MINUIT"
          return
        else:
          self.prevContent    = ''
        pass
        
        #Check if there is an hyperlink
        url                   = self.urlpattern.findall(val)
        nonurl                = self.urlpattern.split(val)
        
        self.lift()
        self.write_lock.acquire()
        self.logfile.write(val.encode('utf-8'))
        self.logfile.flush()
        self.bind('<1>',self.set_focus) #This to allow copy/paste from the console
        self.config(state=NORMAL)
        if(len(url)==0):
          self.insert('end',val,'STDERR' if is_stderr else 'STDOUT')
        else:
          self.insert('end',nonurl[0],'STDERR' if is_stderr else 'STDOUT')
          self.insert('end',url[0],self.hyperlink.add(lambda :webbrowser.open(url[0],2)))
          self.insert('end',nonurl[1],'STDERR' if is_stderr else 'STDOUT')
        pass
        self.see('end')
        self.update()
        self.config(state=DISABLED)
        self.write_lock.release()        
    pass 
pass
