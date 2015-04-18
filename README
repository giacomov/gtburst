-------------------------------
Authors:

Giacomo Vianello, Stanford University (giacomov AT slac stanford edu)
Nicola Omodei, Stanford University (nicola.omodei AT stanford edu)
-------------------------------

gtBurst is a python GUI (Graphical User Interface) which can be used to analyze
Gamma-ray Bursts and Solar Flares observed by the instruments onboard the NASA
Fermi satellite (formerly known as GLAST).

* Requirements:
  - Fermi Science Tools: http://fermi.gsfc.nasa.gov/ssc/data/analysis/software/
  - Python > 2.7 (but not the 3.0 branch)
- tkInter and Tk (>= 8.5)
- scipy (http://www.scipy.org/)
- numpy (it is part of scipy)
- pywcs (https://pypi.python.org/pypi/pywcs)

* Installing:
  1) Download the .tar.gz file somewhere and decompress it. For example,
  save the .tar.gz file in your home directory and decompress it with:
  
  tar zxvf pyBurstAnalysisGUI.tar.gz
  
  Then, set your PATH and PYTHONPATH variables as following:
  
  (for csh/tcsh)
  setenv PATH ~/pyBurstAnalysisGUI/python:${PATH}
  setenv PYTHONPATH ~/pyBurstAnalysisGUI/python:${PYTHONPATH}
   
  (for bash)
  export PATH=~/pyBurstAnalysisGUI/python:${PATH}
  export PYTHONPATH=~/pyBurstAnalysisGUI/python:${PYTHONPATH}
  
  2) Download from http://fermi.gsfc.nasa.gov/ssc/data/access/lat/BackgroundModels.html
  the files gal_2yearp7v6_trim_v0.fits and iso_p7v6source.txt and save them (or copy them)
  in the "data" directory in the installation dir. Using the same example situation as 
  in point 1, you should save them in ~/pyBurstAnalysisGUI/data
  
  3) Set the variables GALACTIC_DIFFUSE_TEMPLATE and ISOTROPIC_TEMPLATE to point to the
  respective template:
  
  (for csh/tcsh)
  setenv GALACTIC_DIFFUSE_TEMPLATE ~/pyBurstAnalysisGUI/data/gal_2yearp7v6_trim_v0.fits
  setenv ISOTROPIC_TEMPLATE ~/pyBurstAnalysisGUI/data/iso_p7v6source.txt
  
  (for bash)
  export GALACTIC_DIFFUSE_TEMPLATE=~/pyBurstAnalysisGUI/data/gal_2yearp7v6_trim_v0.fits
  export ISOTROPIC_TEMPLATE=~/pyBurstAnalysisGUI/data/iso_p7v6source.txt
  
  4)You are set! Create a working directory, enter it and run gtburst.py. For example:
  
  mkdir analysis
  cd analysis
  gtburst.py
  
  and you are good to go
  
* Updating:
  
  If you have git installed (http://git-scm.com/), which is available for all major
  linux distributions and for Max, you can just use the Update feature from within
  the gtburst.py interface. If you don't have it and you don't want to install it,
  then you can always download by hand the latest code from:
  
  http://sourceforge.net/p/gtburst/code/ci/master/tree/
  
  Remember to save it in the same directory in which you saved the first .tar.gz file.


