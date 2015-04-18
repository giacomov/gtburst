#!/usr/bin/env python

import os,sys

print("Testing Science Tools Python wrappers..."),
try:
  from GtApp import GtApp
  st = ['gtbin','gtselect','gtbindef','gtmktime','gtlike',
        'gtexpcube2','gtsrcmaps','gtmodel','gtobssim',
        'gtfindsrc','gtrspgen','gtexpmap','gttsmap',
        'gtltcube','gtbkg','gtdiffrsp']
  
  for s in st:
    fake                      = GtApp(s)
except:
  print("Error!")
  print("\nCannot initialize one of the Science Tools wrapper. Did you initialize Science Tools?\n")
  raise
else:
  print("ok")

print("Testing environment variables..."),
if(os.environ.get('ISOTROPIC_TEMPLATE')==None):
  print("Error!")
  print("\nYou have to set the env. variable ISOTROPIC_TEMPLATE. Refers to the documentation.")
  sys.exit(-1)

if(os.environ.get('GALACTIC_DIFFUSE_TEMPLATE')==None):
  print("Error!")
  print("\nYou have to set the env. variable GALACTIC_DIFFUSE_TEMPLATE. Refers to the documentation.")
  sys.exit(-1)
else:
  print("ok")
  
print("Testing likelihood templates for read access...")
for temp in ['GALACTIC_DIFFUSE_TEMPLATE','ISOTROPIC_TEMPLATE']:
  print("  %s..." %(temp)),
  try:
    f                           = open(os.environ.get(temp))
    f.close()
  except:
    print("Error!")
    print("\nThe %s variables points to %s, which is not readable." %(temp,os.environ.get(temp)))
    sys.exit(-1)
  else:
    print("Using %s" %(os.environ.get(temp)))
pass

print("Testing gtBurst GUI...")
try:
  from gtburst import *
  from GtBurst import *
except:
  print("Error!")
  print("\nCould not import GtBurst! Probably your python is mis-configured. Check the PYTHON_PATH variable.")
  raise

