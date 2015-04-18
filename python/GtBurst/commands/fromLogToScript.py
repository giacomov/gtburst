#! /usr/bin/env python

import sys
import os,re
from GtBurst import commandDefiner

################ Command definition #############################
executableName                = "fromLogToScript"
version                       = "1.0.0"
shortDescription              = "Convert a log from a gtburst session to a script"
author                        = "G.Vianello, giacomov@slac.stanford.edu"
thisCommand                   = commandDefiner.Command(executableName,shortDescription,version,author)

#Define the command parameters
thisCommand.addParameter("logfile","Input log file (typically gtburst.log)",commandDefiner.MANDATORY,extension="log")
thisCommand.addParameter("outscript","Output script",commandDefiner.MANDATORY,partype=commandDefiner.OUTPUTFILE,extension="py")

GUIdescription               = "You should not see this"
thisCommand.setGUIdescription(GUIdescription)

##################################################################

def _yesOrNoToBool(value):      
  if(value.lower()=="yes"):
    return True
  elif(value.lower()=="no"):
    return False
  else:
    raise ValueError("Unrecognized clobber option. You can use 'yes' or 'no'")    
  pass
pass

class Message(object):
  def __init__(self,verbose):
    self.verbose              = bool(verbose)
  pass
  
  def __call__(self,string):
    if(self.verbose):
      print(string)
pass   

def fromLogToScript(**kwargs):
  run(**kwargs)
pass

def run(**kwargs):
  global thisCommand
  if(len(kwargs.keys())==0):
    #Nothing specified, the user needs just help!
    thisCommand.getHelp()
    return
  pass
  
  #Get parameters values
  thisCommand.setParValuesFromDictionary(kwargs)
  try:
    logfile                     = thisCommand.getParValue('logfile')
    outscript                   = thisCommand.getParValue('outscript')
  except KeyError as err:
    print("\n\nERROR: Parameter %s not found or incorrect! \n\n" %(err.args[0]))
    
    #Print help
    thisCommand.getHelp()
    return
  pass
  
  with open(logfile) as f:
    commands                    = []
    while 1:
      try:
        row                       = f.next()
      except:
        break
      match                     = re.findall("- Running (.+) on dataset",row)
      if(len(match)==0):
        continue
      else:
        thisCommand             = "%s.py" % match[0]
        #There is an empty line to jump
        f.next()
        
        #Now go for the parameters
        while 1:
          row2                  = f.next()
          if(len(row2)<2):
            break
          parname,parvalue      = row2.split("=")
          parname               = parname.replace(" ","")
          parvalue              = parvalue.strip()
          parvalue.replace("\n","")
          thisCommand          += " %s='%s'" %(parname,parvalue)
        pass
        commands.append(thisCommand)
      pass
    pass
  pass
  
  outf                        = open(outscript,"w+")
  outf.write("#Usage: source %s\n\n" %(outscript))
  for cmd in commands:
    print("%s\n" % cmd)
    outf.write("\n%s\n" % cmd)
  outf.close()
pass


thisCommand.run = run

if __name__=='__main__':
  thisCommand.greetings()
  #Get all key=value pairs as a dictionary
  args                           = dict(arg.split('=') for arg in sys.argv[1:])
  fromLogToScript(**args)
pass
