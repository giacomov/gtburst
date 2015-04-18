import pyfits
import sys
import os, glob
import shlex, subprocess, shutil
import numpy

#The RSP2 matrix for the GBM are computed by interpolating a grid of
#responses containing Montecarlo-generated rsp for different position of
#the source and different satellite orientations. Thus, the most accurate
#matrix at every time is the closest one.
#We want to weight every applying matrix for every desired time interval
#by the number of total counts contained in that interval

def _callSubprocess(cmdline):
    args                           = shlex.split(cmdline)
    #p = subprocess.check_call(args,stdout=None,stderr=None)
    output, error                  = subprocess.Popen(args,stdout = subprocess.PIPE, stderr= subprocess.PIPE).communicate()
    return output, error
pass

class EventsCounter(object):
  def __init__(self,**kwargs):
    
    eventfile                 = os.path.abspath(os.path.expanduser(os.path.expandvars(kwargs['eventfile'])))
    
    #Check if the event file is a CSPEC
    if(pyfits.getval(eventfile,"DATATYPE",ext=0).find("CSPEC")>=0):
      self.initWithCSPEC(eventfile)
    else:
      self.initWithTTE(eventfile)
    pass  
  pass
  
  def initWithTTE(self,tte):
    f                         = pyfits.open(tte)
    self.inputFile            = 'TTE'
    self.data                 = f["EVENTS",1].data.copy()
    self.eventTimes           = numpy.array(list(self.data.field('TIME')))
    f.close()
  pass
  
  def initWithCSPEC(self,cspec):
    f                         = pyfits.open(cspec)
    self.inputFile            = 'cspec'
    self.data                 = f["SPECTRUM",1].data.copy()
    cspectstarts              = self.data.field("TIME")
    cspectstops               = self.data.field("ENDTIME")
    cspectelapse              = cspectstops-cspectstarts
    #Counts or rates?
    try:
      cspeccounts             = self.data.field("COUNTS")
    except:
      rates                   = self.data.field("RATE")
      cspeccounts              = map(lambda x:x[0]*x[1],zip(rates,cspectelapse))
    pass  
    self.tstarts              = numpy.array(cspectstarts)
    self.tstops               = numpy.array(cspectstops)
    self.counts               = numpy.array(map(lambda x:numpy.sum(x),cspeccounts))
    #Place zeros where QUALITY is > 0 (bad data)
    badDataMask               = (f["SPECTRUM"].data.field('QUALITY')>0)
    self.counts[badDataMask]  *= 0 
    f.close()
  pass
  
  def getNevents(self,tstart,tstop):
    #Return the number of events between tstart and tstop
    #what is the subinterval of the current interval
    if(self.inputFile=="TTE"):
      
      if((tstart < min(self.eventTimes)) or (tstop > max(self.eventTimes))):
        raise RuntimeError("Tstart and tstop out of boundaries")
      
      thisMask                = (self.eventTimes >= tstart) & (self.eventTimes <= tstop)
      nEvents                 = len(thisMask.nonzero()[0])
    
    elif(self.inputFile=="cspec"):
      
      if((tstart < min(self.tstarts)) or (tstop > max(self.tstops))):
        raise RuntimeError("Tstart and tstop out of boundaries")
      
      #Select all interesting intervals
      thisMask                = (self.tstops >= tstart) & (self.tstarts <= tstop)
      
      #Compute the weight for each interval: the weight will be 1 for intervals
      #completely contained between tstart and tstop, and < 1 for the first and
      #last interval. The weighted sum of the counts give the total counts between
      #tstart and tstop, assuming that they are distributed uniformly within the
      #first and last bin
      weight                  = []
      for i in thisMask.nonzero()[0]:
        weight.append((min(tstop,self.tstops[i])-max(tstart,self.tstarts[i]))/(self.tstops[i]-self.tstarts[i]))
      if(len(weight)==0):
        nEvents               = 0
      else:  
        weight                  = numpy.array(weight)
        nEvents                 = numpy.sum(weight*self.counts[thisMask])
      pass
    else:
      raise RuntimeError("Should not get here! this is a bug.")
    return nEvents
  pass
  
pass

def _fixPath(filename):
  return os.path.abspath(os.path.expanduser(os.path.expandvars(filename)))

class TimeIntervals(object):
  def __init__(self,**kwargs):
    
    self.tstarts              = []
    self.tstops               = []
    self.counts               = []
    
    eventsCounter                     = EventsCounter(eventfile=_fixPath(kwargs['eventfile']))
    
    timeBinsFile                      = pyfits.open(_fixPath(kwargs['timeBinsFile']))
    for rowID in range(timeBinsFile["TIMEBINS"].data.shape[0]):
      curTstart                       = timeBinsFile["TIMEBINS"].data[rowID][0]
      curTstop                        = timeBinsFile["TIMEBINS"].data[rowID][1]
      self.tstarts.append(curTstart)
      self.tstops.append(curTstop)
      #Count how many events are contained in the TTE file between tstart and tstop
      self.counts.append(eventsCounter.getNevents(curTstart,curTstop))
    pass
    timeBinsFile.close()
  pass
pass

def RSPweight(**kwargs):    
    '''
  Weight the response matrices contained in the rsp file.
  Usage:
    
    RSPweight(eventfile=eventfile,timeBinsFile=timeBinsFile,rsp2file=rsp2file,
              outfile=outfile,triggerTime=triggerTime)
    
    where eventfile can be either a TTE/FT1 file or a CSPEC file.
    '''    
    timeIntervals                    = TimeIntervals(**kwargs)
    
    rsp2                             = _fixPath(kwargs['rsp2file'])
    out                              = _fixPath(kwargs['outfile'])
    #The trigger time is only for printing purposes: if specified,
    #all the messages from the program will contain time intervals referred
    #to the trigger time, otherwise they will be in MET
    if('triggerTime' in kwargs.keys()):
      trigger                        = kwargs['triggerTime']
    else:
      trigger                        = 0
    #name for the output
    outrsp                           = out
    
    #Open files
    rsp2File                          = pyfits.open(rsp2)
    
    #Get instrument name
    try:
      instrument                        = pyfits.getval(_fixPath(kwargs['eventfile']),"INSTRUME",extname="EVENTS",extver=1)
    except:
      try:
        instrument                        = pyfits.getval(_fixPath(kwargs['eventfile']),"INSTRUME",extname="SPECTRUM",extver=1)
      except:
        instrument                        = "UNKN-INSTRUME"
    #For every interval contained in the time bins file
    #find the applying matrices and compute the weight (if necessary)
    nIntervals                        = len(timeIntervals.tstarts)
    nMatrix                           = len(rsp2File)
    createdRspNames                   = []
    eventsCounter                     = EventsCounter(**kwargs)
    for tstart,tstop,nEvents,intervalNumber in zip(timeIntervals.tstarts,
                                                   timeIntervals.tstops,
                                                   timeIntervals.counts,
                                                   range(nIntervals)):
      print("\nInterval: %s - %s" % (tstart-trigger,tstop-trigger))
      
      #find the RSP matrices falling in the current tstart-tstop interval
      rspList                         = []
      rspStarts                       = []
      rspStops                        = []
      firstResponse                   = True
      for extNumber in range(nMatrix):
      
        if(rsp2File[extNumber].name=="SPECRESP MATRIX" or 
           rsp2File[extNumber].name=="MATRIX"):                    
                     
          curHeader                           = rsp2File[extNumber].header
          
          #Check that the instrument is the same of the TTE file
          instrument2                         = curHeader["INSTRUME"]
          if(instrument2!=instrument):
            print("WARNING: the Events file %s and the response matrix file %s refers to different instruments" % (instrument,instrument2))
          pass
          
          #Find the start and stop time of the interval covered 
          #by this response matrix
          headerStart                         = curHeader["TSTART"]
          headerStop                          = curHeader["TSTOP"]

          #The matrix cover the period going from the middle point between its start
          #time and the start time of the previous matrix (or its start time if it is the
          #first matrix of the file), and the middle point between its start time and its
          #stop time (that is equal to the start time of the next one):
          #
          #           tstart                             tstop
          #             |==================================|
          # |--------------x---------------|-----------x-----------|----------x--..
          #rspStart1    rspStop1=    headerStart2  rspStop2= headerStart3  rspStop3
          #             rspStart2                  rspStart3
          #           
          #covered by: |m1 |           m2             | m3|
          #
          
          if(firstResponse):
            #This is the first matrix
            if(extNumber==len(rsp2File)-1):
              #This is both the first both the last matrix
              rspStart                          = headerStart
              rspStop                           = headerStop 
            else:
              rspStart                          = headerStart
              rspStop                           = (headerStart+headerStop)/2.0
              firstResponse                     = False
            pass
          elif(extNumber==len(rsp2File)-1):
            #This is the last matrix
            rspStart                          = prevRspStop
            rspStop                           = headerStop            
          else:
            rspStart                          = prevRspStop
            rspStop                           = (headerStart+headerStop)/2.0    
          pass
          
          #Save the stop time for the next iteration of the loop
          prevRspStop                         = rspStop
                
          #Check if the current matrix covers at least a portion of the 
          #start-stop time interval
          if( rspStop >= tstart and rspStart <= tstop):
            #Found a matrix covering a part of the interval:
            #adding it to the list:
            rspList.append(fixMatrixHDU(rsp2File[extNumber]))
            
            #Get the "true" start time of the time sub-interval covered by this matrix
            trueRspStart                       = max(rspStart,tstart)
            
            #Get the "true" stop time of the time sub-interval covered by this matrix
            if(extNumber==len(rsp2File)-1):
              #Since there are no matrices after this one, this has to cover until the end of the interval
              if(tstop > rspStop):
                print("\nWARNING: RSPweight: The RSP file does not cover the required time interval.")
                print("    The last response should cover from %s to %s, but we'll use it" % (trueRspStart, rspStop))
                print("    to cover until the end of the time interval (%s)." % (tstop))
                trueRspStop                      = tstop
              else:
                trueRspStop                      = tstop 
            else:
              trueRspStop                      = min(rspStop,tstop)
            pass
            
            #Save the true start and stop
            rspStarts.append(trueRspStart)
            rspStops.append(trueRspStop)
            
            print("  Matr. in ext #%s covers %s - %s" % (extNumber,trueRspStart-trigger,trueRspStop-trigger))
            if(rspStop >= tstop):
              #This matrix cover after the tstop,
              #no reason to analize the other matrices
              #pass
              break
            pass
          pass
        
        pass
      
      pass
      
      weight                            = []
    
      if(len(rspList) > 1):
        #We want to weight matrices by number of counts
        #so we need the number of events falling in the current
        #time interval
        
        #Number of total events contained in the interval
        nThisTotalEvt                   = nEvents

        print("\n  Total counts for this interval:        %s" %(nThisTotalEvt))

        if(nThisTotalEvt <= 0): 
          print("  Counts is zero: no signal here. Weight will be exposure-based.")
          #Weight according to the exposure
          if(sum(weight)==0):
            for index,rsp in enumerate(rspList):
              thisWeight                      = (rspStops[index]-rspStarts[index])/(tstop-tstart)
              weight.append(thisWeight)
              print("  Weight for response %s - %s:           %s" % (rspStarts[index]-trigger,rspStops[index]-trigger,thisWeight))
            pass
          pass
        else:
          #Weight according to the counts
          #now look upon the selected events, searching for events
          #falling in the interval covered by each
          #response matrix
          for index,rsp in enumerate(rspList):
            rspStart                          = rspStarts[index]
            rspStop                           = rspStops[index]
            
            #how many events of the time interval contained here?
            nThisRspEvt                       = eventsCounter.getNevents(rspStart,rspStop)

            #Compute the weight
            if(nThisRspEvt > 0):
              thisWeight                      = float(nThisRspEvt)/float(nThisTotalEvt)
            else:
              thisWeight                      = 0
            pass
            
            #Append the weight to the list of weights
            weight.append(thisWeight)
            
            #Print information
            print("  Weight for response %s - %s:           %s" % (rspStart-trigger,rspStop-trigger,thisWeight))
            print("  Counts in time covered by this rsp:  %s" % nThisRspEvt)      
          pass
        pass
        
        #Now, if the sum of the weight is not 1, redistribuite the lacking weight 
        #according to the exposure. This can happen due to precision problems
        if(sum(weight)!=1):
          lackingWeight                     = 1.0-sum(weight)
          for index,rsp in enumerate(rspList):
            thisExposureWeight              = (rspStops[index]-rspStarts[index])/(tstop-tstart)
            weight[index]                  += (thisExposureWeight*lackingWeight)
          pass
        pass
        
        print("\nTotal weight ---> %s" %(sum(weight)))
        
      else:        
        #There is only one matrix...
        weight                              = [1]
      pass 
      
      print("\n")
      
      #Use addrmf to add and weight the response matrix
      #We don't use directly pyFits because dealing with response matrices
      #can be dangerous due to the variable lenght column,
      #and other features, so we leave the work to a specialized tool
      
      #we need to create a file for every matrix, and an ascii file
      #containing the list of those files and the weights to be applied
      asciiFilename                           = "__rspweight_rspList.ascii"
      asciiFile                               = open(asciiFilename,'w')
      asciiFile.write('')
      
      #Loop on the matrices and sum them
      names                                   = []
      for rsp_i in range(len(rspList)):
        #Decide a temporary filename
        name                                  = "__rspweight_matrix"+str(rsp_i)+".rsp"
        names.append(name)
        
        primaryHDU                            = rsp2File[0].copy()
        eboundsHDU                            = rsp2File['EBOUNDS'].copy()
        responseHDU                           = rspList[rsp_i].copy()
        HDUlist                               = pyfits.HDUList([primaryHDU,eboundsHDU,responseHDU])
        HDUlist.writeto(name,output_verify='fix',clobber=True)
                        
        if(instrument.find("GBM")>=0):
          # FIX the wrong GBM matrices
          data                                  = pyfits.open(name,'update')
          #EBOUNDS:
          #Find what is the tlminColumn column                  
          columns                               = data['EBOUNDS'].data.names          
          tlminID                               = columns.index('CHANNEL')+1           
        
          #Find the number of channels (usually 128)
          nChannels                             = data['EBOUNDS'].data.size
        
          #Fix the CHANNEL column, and TLMIN/TLMAX keywords
          data['EBOUNDS'].data.field('CHANNEL')[:]=numpy.array(range(1,nChannels+1))
          data['EBOUNDS'].header.set("TLMIN%s" %(tlminID),1)
          data['EBOUNDS'].header.set("TLMAX%s" %(tlminID),nChannels)
          #SPECRESP MATRIX
          #Now we have to correct the rows whith wrong F_CHAN and N_CHAN values:
          #There are rows where F_CHAN = 128, and N_CHAN = 1, but the only element not null
          #in the row is the first, thus it should be: F_CHAN = 1, N_CHAN = 1
        
          for row in range(nChannels):
            if(data['SPECRESP MATRIX'].data.field('F_CHAN')[row]==128 and
               data['SPECRESP MATRIX'].data.field('N_CHAN')[row]==1):
            
              #We have a possibly wrong row
              #Try to access the channel 128 of the matrix
              try:
                data['SPECRESP MATRIX'].data.field('MATRIX')[row][127]
              except:
                #Impossible to access it, thus the values are wrong. Fix them
                data['SPECRESP MATRIX'].data.field('F_CHAN')[row] = numpy.array([1])
                data['SPECRESP MATRIX'].data.field('N_CHAN')[row] = numpy.array([1]) 
              pass
            pass   
          pass
          #Find what is the tlminColumn column                  
          columns                                            = data['SPECRESP MATRIX'].data.names          
          tlminID                                            = columns.index('F_CHAN')+1 
          data['SPECRESP MATRIX'].header.set("TLMIN%s" %(tlminID),1)
          data['SPECRESP MATRIX'].header.set("TLMAX%s" %(tlminID),nChannels)
          data.close()
        pass        
        
        asciiFile.write(name+" "+str(weight[rsp_i])+"\n")
      pass
      asciiFile.close()
      
      #Decide a name for the output matrix for this interval
      thisRspName                          = "__rspweight_interval"+str(intervalNumber)+".rsp"
      createdRspNames.append(thisRspName)
      
      if(len(names)==1):
        #Only one matrix. No need to weight
        shutil.copy(names[0],thisRspName)
      else:
        #Run addrmf and weight the relevant matrices
        cmdline                              = "addrmf @%s rmffile=%s clobber=yes" % (asciiFilename,thisRspName)
        print("\n %s \n" %(cmdline))
        
        out, err                             = _callSubprocess(cmdline)
        
        print out
        print err
      pass
      #clean up
      os.remove(asciiFilename)
    pass
    
    #now append all the produced matrix in one RSP2 file
    #Take the PRIMARY extension from the input RSP2 file
    primary                          = rsp2File[0].copy()
    primary.header.set("DRM_NUM",nIntervals)
    primary.header.set("TSTART",timeIntervals.tstarts[0])
    primary.header.set("TSTOP",timeIntervals.tstops[-1])
    primary.writeto(outrsp,clobber='True')
    
    #Get the EBOUNDS extension from the first matrix
    firstRsp                    = pyfits.open(createdRspNames[0])
    ebounds                     = firstRsp['EBOUNDS'].copy()
    firstRsp.close()
    
    #Reopen the file just created
    outRsp2                           = pyfits.open(outrsp,'update')
    outRsp2.append(ebounds)
    
    #now write an extension for each interval
    for i in range(nIntervals):
      thisRsp                   = pyfits.open(createdRspNames[i])
      
      try:
        curM                    = fixMatrixHDU(thisRsp["SPECRESP MATRIX"]).copy()
        name                    = "SPECRESP MATRIX"
      except:
        try:
          curM                  = fixMatrixHDU(thisRsp["SPECRESP MATRIX"]).copy()
          name                  = "MATRIX"
        except:
          raise RuntimeError("Something gone wrong. Invalid file produced by the weighting algorithm.")
      pass
      
      thisRsp.close()
      
      curHeader               = curM.header
      curData                 = curM.data
      
      #Update TSTART and TSTOP
      curHeader.set("TSTART",timeIntervals.tstarts[intervalNumber])
      curHeader.set("TSTOP",timeIntervals.tstops[intervalNumber])
      
      #Update RSP_NUM keyword
      curHeader.set("RSP_NUM",i+1)
      
      #update EXTVER keyword
      curHeader.set("EXTVER",i+1)
      
      #Add history
      history="This is a matrix computed by weighting applying matrices contained in "+rsp2
      curHeader.add_history(history)
      print("Appending matrix number %s..." %(i+1))
      #Write this as an extension in the output file      
      outRsp2.append(curM)
    pass
    #Closing everything
    outRsp2.close()
       
    #Close files
    rsp2File.close()
    #Cleanup
    print("Cleaning up...")
    fileToDelete              = glob.glob("__rspweight*")
    for f in fileToDelete:
      os.remove(f)
pass

def fixMatrixHDU(matrixHDU):
  #This creates a copy of the input matrix with all variable-length arrays converted to fixed length,
  #of the smallest possible size.
  #This is needed because pyfits makes all sort of fuckups with variable-length arrays

  newcols = []
  
  for col in matrixHDU.columns:
    if(col.format.find("P")==0):
      #Variable-length
      newMatrix               = variableToMatrix(matrixHDU.data.field(col.name))
      length                  = len(newMatrix[0])
      coltype                 = col.format.split("(")[0].replace("P","")
      newFormat               = '%s%s' %(length,coltype)
      newcols.append(pyfits.Column(col.name,newFormat,col.unit,col.null,col.bscale,col.bzero,col.disp,
                                 col.start,col.dim,newMatrix))
    else:
      newcols.append(pyfits.Column(col.name,col.format,col.unit,col.null,col.bscale,col.bzero,col.disp,
                                 col.start,col.dim,matrixHDU.data.field(col.name)))
  pass

  newtable                    = pyfits.new_table(newcols,header=matrixHDU.header)
  return newtable
pass

def variableToMatrix(variableLengthMatrix):
  '''This take a variable length array and return it in a properly formed constant length array'''
  nrows                          = len(variableLengthMatrix)
  ncolumns                       = max([len(elem) for elem in variableLengthMatrix])
  matrix                         = numpy.zeros([nrows,ncolumns])
  for i in range(nrows):
    for j in range(ncolumns):
      try:
        matrix[i,j]                = variableLengthMatrix[i][j]
      except:
        pass
  return matrix
pass
