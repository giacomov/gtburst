#Author:
# G.Vianello (giacomov@slac.stanford.edu, giacomo.slac@gmail.com)


import numpy
import os,sys
import pyfits
import math
from GtApp import GtApp
import scipy.optimize
import warnings

#This is to speed up
log                           = numpy.log

#Activate this to compare with ROOT results
test                          = False

class Fitter(object):
  '''
  This class is a wrapper around a given ROOT TF1, to multiply this TF1 by the exposure.
  This way we can fit a function giving the rate to a light curve in counts, using
  the Poisson likelihood.
  '''
  def __init__(self,tf1,t,exposure):
    import ROOT
    
    self.tf1                  = tf1.Clone()

    #Fill a TGraph with the exposure, so that we can evaluate the
    #exposure later using the Eval() method of the TGraph class
    self.exposureGraph        = ROOT.TGraph()
    for i,tt,exp in zip(range(len(t)),t,exposure):
      self.exposureGraph.SetPoint(i,tt,exp)
    pass  
  pass
  
  def __call__(self,x,par):
    xx                        = x[0]
    for i,p in enumerate(par):
      self.tf1.SetParameter(i,p)
    pass  
    
    return self.tf1.Eval(xx)*self.exposureGraph.Eval(xx)
    
  pass
  
  def getParameter(self,i):
    return self.tf1.getParameter(i)
  pass
  
  def Draw(self,options=""):
    self.tf1.Draw(options)
  pass
  
pass
  
#The following method is for test purposes only
def fitWithROOT(x,y,exposure,polynomial,savePNG=False):
    '''
    Fit a light curve (in counts) with the given polynomial using ROOT. This is
    for comparison purposes only.
    '''
    #Test
    #We import here ROOT so it is not a global dependency,
    #but it is needed only when doing tests
    import ROOT
    
    print("\n\nWARNING: the comparison between ROOT and the present module is meaningful only")
    print("        if you are using a contiguous time interval for the background,") 
    print("        otherwise results WILL BE different")       
    
    zeros                     = numpy.zeros(len(x))
    binsize                   = (x[1]-x[0])
    h                         = ROOT.TH1D("test","ciaps",len(x),x[0]-binsize/2.0,x[-1]+binsize/2.0)
    for i,xx,yy in zip(range(len(x)),x,y):
      h.SetBinContent(i+1,yy)
      h.SetBinError(i+1,math.sqrt(yy))
    pass
    
    polyname                  = "pol%i" %(polynomial.degree)
    rootPolynomial            = ROOT.TF1("rootPoly",polyname,min(x),max(x))
    parameters                = polynomial.getParams()
    for i,p in enumerate(parameters):
      rootPolynomial.SetParameter(i,p)
    pass
    
    fitter                    = Fitter(rootPolynomial,x,exposure)
    fitfunction               = ROOT.TF1("fitfun",fitter,min(x),max(x),len(parameters))
    
    canvas                    = ROOT.TCanvas()   
    h.Fit(fitfunction,"S")
    h.Fit(fitfunction,"LE")
    #Compare results
    ratio                     = []
    for i,p in enumerate(parameters):
      thisRatio               = fitfunction.GetParameter(i)/p
      print("\nParam. %s, ratio (ROOT/thisModule) = %s" %(i,thisRatio))
      ratio.append(thisRatio)
    pass
    h.Draw("HIST")
    fitter.Draw("same")
    canvas.Update()
    if(savePNG):
      canvas.Print("root.png") 
pass

class LogLikelihood(object):
  '''
  Implements a Poisson likelihood (i.e., the Cash statistic). Mind that this is not
  the Castor statistic (Cstat). The difference between the two is a constant given
  a dataset. I kept Cash instead of Castor to make easier the comparison with ROOT
  during tests, since ROOT implements the Cash statistic.
  '''
  def __init__(self,x,y,model,**kwargs):
    self.x                    = x
    self.y                    = y
    self.model                = model
    self.parameters           = model.getParams()
    
    #Initialize the exposure to 1.0 (i.e., non-influential)
    #It will be replaced by the real exposure if the exposure keyword
    #have been used
    self.exposure             = numpy.zeros(len(x))+1.0
        
    for key in kwargs.keys():
      if  (key.lower()=="exposure"):            
        self.exposure = numpy.array(kwargs[key])
    pass  
        
  pass
  
  def _evalLogM(self,M):
    #Evaluate the logarithm with protection for negative or small
    #numbers, using a smooth linear extrapolation (better than just a sharp
    #cutoff)
    tiny                      = numpy.float64(numpy.finfo(M[0]).tiny)
    
    nontinyMask               = (M > 2.0*tiny)
    tinyMask                  = numpy.logical_not(nontinyMask)
    
    if(len(tinyMask.nonzero()[0])>0):      
      logM                     = numpy.zeros(len(M))
      logM[tinyMask]           = numpy.abs(M[tinyMask])/tiny + log(tiny) -1
      logM[nontinyMask]        = log(M[nontinyMask])
    else:
      logM                     = log(M)
    return logM
  pass
  
  def __call__(self, parameters):
    '''
      Evaluate the Cash statistic for the given set of parameters
    '''
    
    #Compute the values for the model given this set of parameters
    self.model.setParams(parameters)
    M                         = self.model(self.x)*self.exposure
    Mfixed,tiny               = self._fixPrecision(M)
    
    #Replace negative values for the model (impossible in the Poisson context)
    #with zero
    negativeMask              = (M < 0)
    if(len(negativeMask.nonzero()[0])>0):
      M[negativeMask]         = 0.0
    pass
    
    #Poisson loglikelihood statistic (Cash) is:
    # L = Sum ( M_i - D_i * log(M_i))   
    
    logM                      = self._evalLogM(M)
    
    #Evaluate v_i = D_i * log(M_i): if D_i = 0 then the product is zero
    #whatever value has log(M_i). Thus, initialize the whole vector v = {v_i}
    #to zero, then overwrite the elements corresponding to D_i > 0
    d_times_logM              = numpy.zeros(len(self.y))
    nonzeroMask               = (self.y > 0)
    d_times_logM[nonzeroMask] = self.y[nonzeroMask] * logM[nonzeroMask]
    
    logLikelihood             = numpy.sum( Mfixed - d_times_logM )

    return logLikelihood    
  pass
  
  def _fixPrecision(self,v):
    '''
      Round extremely small number inside v to the smallest usable
      number of the type corresponding to v. This is to avoid warnings
      and errors like underflows or overflows in math operations.
    '''
    tiny                      = numpy.float64(numpy.finfo(v[0]).tiny)
    zeroMask                  = (numpy.abs(v) <= tiny)
    if(len(zeroMask.nonzero()[0])>0):
      v[zeroMask]               = numpy.sign(v[zeroMask])*tiny
    
    return v, tiny
  pass
  
  def getFreeDerivs(self,parameters=None):
    '''
    Return the gradient of the logLikelihood for a given set of parameters (or the current
    defined one, if parameters=None)
    '''
    #The derivative of the logLikelihood statistic respect to parameter p is:
    # dC / dp = Sum [ (dM/dp)_i - D_i/M_i (dM/dp)_i]
    
    #Get the number of parameters and initialize the gradient to 0
    Nfree                     = self.model.getNumFreeParams()
    derivs                    = numpy.zeros(Nfree)
    
    #Set the parameters, if a new set has been provided
    if(parameters!=None):
      self.model.setParams(parameters)
    pass
    
    #Get the gradient of the model respect to the parameters
    modelDerivs               = self.model.getFreeDerivs(self.x)*self.exposure
    #Get the model
    M                         = self.model(self.x)*self.exposure
    
    M, tinyM                  = self._fixPrecision(M)
    
    #Compute y_divided_M = y/M: inizialize y_divided_M to zero
    #and then overwrite the elements for which y > 0. This is to avoid
    #possible underflow and overflow due to the finite precision of the
    #computer
    y_divided_M               = numpy.zeros(len(self.y))
    nonzero                   = (self.y > 0)
    y_divided_M[nonzero]      = self.y[nonzero]/M[nonzero]
       
    for p in range(Nfree):
      thisModelDerivs, tinyMd = self._fixPrecision(modelDerivs[p])
      derivs[p]               = numpy.sum(thisModelDerivs * (1.0 - y_divided_M) )
    pass
    
    return derivs
    
  pass
    
pass

class Polynomial(object):
  def __init__(self,params):
    self.params               = params
    self.degree               = len(params)-1
    
    #Build an empty covariance matrix
    self.covMatrix            = numpy.zeros([self.degree+1,self.degree+1])
  pass
  
  def horner(self, x):
    """A function that implements the Horner Scheme for evaluating a
    polynomial of coefficients *args in x."""
    result = 0
    for coefficient in self.params[::-1]:
        result = result * x + coefficient
    return result
  pass
  
  def __call__(self,x):
    return self.horner(x)
  pass
  
  def __str__(self):        
    #This is call by the print() command
    #Print results
    output                    = "\n------------------------------------------------------------"
    output                   += '\n| {0:^10} | {1:^20} | {2:^20} |'.format("COEFF","VALUE","ERROR")
    output                   += "\n|-----------------------------------------------------------"
    for i,parValue in enumerate(self.getParams()):
      output                 += '\n| {0:<10d} | {1:20.5g} | {2:20.5g} |'.format(i,parValue,math.sqrt(self.covMatrix[i,i]))
    pass
    output                   += "\n------------------------------------------------------------"
    
    return output
  pass
  
  def setParams(self,parameters):
    self.params               = parameters
  pass

  def getParams(self):
    return self.params
  pass
  
  def getNumFreeParams(self):
    return self.degree+1
  pass
  
  def getFreeDerivs(self,x):
    Npar                      = self.degree+1
    freeDerivs                = []
    for i in range(Npar):
      freeDerivs.append(map(lambda xx:pow(xx,i),x))
    pass
    return numpy.array(freeDerivs)
  pass
  
  def computeCovarianceMatrix(self,statisticGradient):
    self.covMatrix            = computeCovarianceMatrix(statisticGradient,self.params)
    #Check that the covariance matrix is positive-defined
    negativeElements          = (numpy.matrix.diagonal(self.covMatrix) < 0)
    if(len(negativeElements.nonzero()[0]) > 0):
      raise RuntimeError("Negative element in the diagonal of the covariance matrix. Try to reduce the polynomial grade.")
  pass  
  
  def getCovarianceMatrix(self):
    return self.covMatrix
  pass
  
  def integral(self,xmin,xmax):
    '''
    Evaluate the integral of the polynomial between xmin and xmax
    '''
    integralCoeff             = [0]
    integralCoeff.extend(map(lambda i:self.params[i-1]/float(i),range(1,self.degree+1+1)))
    
    integralPolynomial        = Polynomial(integralCoeff)
    
    return integralPolynomial(xmax) - integralPolynomial(xmin)
  pass
  
  def integralError(self,xmin,xmax):
    # Based on http://root.cern.ch/root/html/tutorials/fit/ErrorIntegral.C.html
    
    #Set the weights
    i_plus_1                  = numpy.array(range(1,self.degree+1+1),'d')
    def evalBasis(x):
      return (1/i_plus_1) * pow(x,i_plus_1)
    c                         = evalBasis(xmax) - evalBasis(xmin)
    
    #Compute the error on the integral
    err2                      = 0.0
    nPar                      = self.degree+1
    parCov                    = self.getCovarianceMatrix()
    for i in range(nPar):
      s                       = 0.0
      for j in range(nPar):
        s                    += parCov[i,j] * c[j]
      pass
      err2                   += c[i]*s
    pass
    
    return math.sqrt(err2)
  pass
  
pass

def computeCovarianceMatrix(grad,par,full_output=False,
          init_step=0.01,min_step=1e-12,max_step=1,max_iters=50,
          target=0.1,min_func=1e-7,max_func=4):
          
    """Perform finite differences on the _analytic_ gradient provided by user to calculate hessian/covariance matrix.

    Positional args:
        grad                : a function to return a gradient
        par                 : vector of parameters (should be function minimum for covariance matrix calculation)

    Keyword args:

        full_output [False] : if True, return information about convergence, else just the covariance matrix
        init_step   [1e-3]  : initial step size (0.04 ~ 10% in log10 space); can be a scalar or vector
        min_step    [1e-6]  : the minimum step size to take in parameter space
        max_step    [1]     : the maximum step size to take in parameter sapce
        max_iters   [5]     : maximum number of iterations to attempt to converge on a good step size
        target      [0.5]   : the target change in the function value for step size
        min_func    [1e-4]  : the minimum allowable change in (abs) function value to accept for convergence
        max_func    [4]     : the maximum allowable change in (abs) function value to accept for convergence
    """

    nparams                   = len(par)
    step_size                 = numpy.ones(nparams)*init_step
    step_size                 = numpy.maximum(step_size,min_step*1.1)
    step_size                 = numpy.minimum(step_size,max_step*0.9)
    hess                      = numpy.zeros([nparams,nparams])
    min_flags                 = numpy.asarray([False]*nparams)
    max_flags                 = numpy.asarray([False]*nparams)

    def revised_step(delta_f,current_step,index):
        if (current_step == max_step):
            max_flags[i]      = True
            return True,0
        
        elif (current_step == min_step):
            min_flags[i]      = True
            return True,0
        
        else:
            adf               = abs(delta_f)
            if adf < 1e-8:
                # need to address a step size that results in a likelihood change that's too
                # small compared to precision
                pass
                
            if (adf < min_func) or (adf > max_func):
                new_step      = current_step/(adf/target)
                new_step      = min(new_step,max_step)
                new_step      = max(new_step,min_step)
                return False,new_step
            else:
                return True,0
    
    iters                     = numpy.zeros(nparams)
    for i in xrange(nparams):
        converged             = False
        
        for j in xrange(max_iters):        
            iters[i]         += 1
            
            di                = step_size[i]
            par[i]           += di
            g_up              = grad(par)
            
            par[i]           -= 2*di
            g_dn              = grad(par)
            
            par[i]           += di
            
            delta_f           = (g_up - g_dn)[i]
            
            converged,new_step = revised_step(delta_f,di,i)
            #print 'Parameter %d -- Iteration %d -- Step size: %.2e -- delta: %.2e'%(i,j,di,delta_f)
            
            if converged: 
              break
            else: 
              step_size[i] = new_step
        pass
        
        hess[i,:] = (g_up - g_dn) / (2*di)  # central difference
        
        if not converged:
            print 'Warning: step size for parameter %d (%.2g) did not result in convergence.'%(i,di)
    try:
        cov = numpy.linalg.inv(hess)
    except:
        print 'Error inverting hessian.'
        raise Exception('Error inverting hessian')
    if full_output:
        return cov,hess,step_size,iters,min_flags,max_flags
    else:
        return cov
    pass
pass
