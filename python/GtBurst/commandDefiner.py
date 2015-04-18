import collections
import textwrap
import os
from GtBurst.version import getVersion,getPackageName

MANDATORY                     = True
OPTIONAL                      = False
INPUTFILE                     = 99999
DATASETFILE                   = 11111
GENERICFILE                   = 33333
OUTPUTFILE                    = 55555
PYTHONONLY                    = 00000
HIDDEN                        = 22222
INDEF                         = -99999

class UserError(RuntimeError):
   def __init__(self, message):
      self.message = message
pass

class Parameter(object):
  def __init__(self,parname,description,mandatory=True,defaultValue=None,**kwargs):
    self.parname              = parname
    self.description          = description
    self.mandatory            = bool(mandatory)
    self.defaultValue         = defaultValue
    self.value                = defaultValue
    
    self.type                 = INDEF
    self.extension            = "*"
    self.possibleValues       = []
    for key in kwargs.keys():
      if   key.lower()=="partype":        self.type           = kwargs[key]
      elif key.lower()=="extension":      self.extension      = kwargs[key]
      elif key.lower()=="possiblevalues": self.possibleValues = map(lambda x:x.lower(),kwargs[key])
  pass
  
  def setValue(self,value):
    if(self.possibleValues!=[] and value.lower() not in self.possibleValues):
      raise ValueError("Value %s is not a valid value for parameter %s. Possible values are: %s" %(value,self.parname,",".join(self.possibleValues)))
    self.value                = value
  pass
  
  def getValue(self):
    return self.value
  pass
  
  def isMandatory(self):
    return self.mandatory
  pass
pass

class Command(object):
  def __init__(self,name,description,version,author):
    self.name                 = name
    self.version              = version
    self.author               = author
    self.description          = description
    self.GUIdescription       = "You should not see this"
    #The definedParameters dictionary contains parameter names as keys and Parameter classes as values
    self.definedParameters    = collections.OrderedDict()
  pass
  
  def greetings(self):
    print("This is %s (%s %s)\nAuthor: %s\n" %(self.name,getPackageName(),getVersion(),self.author))
  pass
  
  def addParameter(self,parname,description,mandatory=True,defaultValue=None,**kwargs):
    self.definedParameters[parname] = Parameter(parname,description,mandatory,defaultValue,**kwargs)
  pass
  
  def getParValue(self,parname):
    return self.definedParameters[parname].getValue()
  pass
  
  def changeParName(self,oldname,newname):
    value                     = self.definedParameters[oldname]
    self.definedParameters[newname] = value
    del self.definedParameters[oldname]
  
  def setParValue(self,parname,value):
    self.definedParameters[parname].setValue(value)
  pass
   
  def setParValuesFromDictionary(self,inputDict):
    for parname, parameter in self.definedParameters.iteritems():
      try:
        if(parameter.type==INPUTFILE):
          parameter.setValue(os.path.abspath(os.path.expanduser(inputDict[parname])))
        else:
          parameter.setValue(inputDict[parname])
      except KeyError:
        if(parameter.isMandatory()):
          raise RuntimeError("You have to specify parameter %s." %(parname))
        else:
          #This is an optional parameter
          pass
        pass
      pass
    pass
  pass
    
  def setGUIdescription(self,description):
    self.GUIdescription       = description
  pass  
  
  def getGUIdescription(self):
    return self.GUIdescription
  
  def getHelp(self):
    #Print a help message
    message                   = ''
    message                  += "%s" %(self.description)
    message                  += "\n"
    message                  += "\nParameters:\n"
    for parname, parameter in self.definedParameters.iteritems():
      if(parameter.isMandatory()):
        description             = parameter.description
      elif(parameter.type==PYTHONONLY):
        continue
      else:
         description           = "(OPTIONAL) %s" %(parameter.description) 
      pass
      descriptionLines        = textwrap.wrap(description,40)
      message                += "\n{0:20s}: {1:40s}".format(parname, descriptionLines[0])
      for i in range(1,len(descriptionLines)):
        message              += "\n{0:20s}  {1:40s}".format(" ",descriptionLines[i])
      pass
      if(parameter.isMandatory()==False):
        message              += "\n{0:20s}  {1:40s}".format(" ","(Default: %s)" %(parameter.defaultValue))
    pass
    print(message)
  pass
pass    
