import matplotlib
import matplotlib.pyplot as plt
import numpy as np


def plot_time_resolved_like(time_resolved_results_files, trigger_names, redshift=0.0,
                            flux_type='photonFlux', plot_photon_index=True,
                            colors=["#1f78b4", "#33a02c","#fb9a99","#e31a1c","#fdbf6f","#ff7f00","#cab2d6","#6a3d9a"],
                            plot_args=None):
             
         
    if plot_photon_index:
    
        fig, (ax1, ax2) = plt.subplots(2,1, sharex=True, gridspec_kw={'height_ratios': [3, 1]})
    
    else:
        
        fig, ax1 = plt.subplots(1,1)
    
    if isinstance(time_resolved_results_files, str):
        
        time_resolved_results_files = [time_resolved_results_files]
        
        triggernames = [triggernames]
    
    assert len(time_resolved_results_files) <= len(colors)
    assert len(time_resolved_results_files) <= len(trigger_names)
    
    if plot_args is None:
        
        plot_args = {}
    
    all_mins = []
    all_maxs = []
    
    all_tmins = []
    all_tmaxs = []
    
    for i, (trigger_name, time_resolved_results_file) in enumerate(zip(trigger_names, time_resolved_results_files)):
        
        color = colors[i]
        
        time_resolved_results = np.recfromtxt(time_resolved_results_file, names=True, delimiter=" ")
        
        tstarts = time_resolved_results["tstart"]
        tstops = time_resolved_results["tstop"]
    
        median = (tstarts + tstops) / 2.0 / (1 + float(redshift))
        start = tstarts / (1 + float(redshift))
        stop = tstops / (1 + float(redshift))
    
        y = time_resolved_results[flux_type]
        Dy = time_resolved_results[flux_type+"Error"]
    
        # Remove the "<" sign in the upper limits entries
    
        try:
    
            y = np.core.defchararray.replace(y, "<", "", count=None)
    
        except:
    
            print('No Upper-Limits Found in %s.' % (trigger_name))
    
        # Remove the "n.a." from the error column in the cases where there are upper limits,
        # and replace it with 0
    
        try:
    
            Dy = np.core.defchararray.replace(Dy, "n.a.", "0",
                                              count=None)
            
        except:
    
            print('No 0-Error Found in %s.' % (trigger_name))
    
        bar = 0.5
    
        Y = np.array(y, dtype=float)
    
        DY = np.array(Dy, dtype=float)
    
        if (DY > 0).sum() > 0:  # if sum() gives a non-zero value then there are error values
    
            ax1.errorbar(median[DY > 0], Y[DY > 0],
                         xerr=[median[DY > 0] - start[DY > 0], stop[DY > 0] - median[DY > 0]],
                         mfc=color, mec=color, ecolor=color,
                         yerr=DY[DY > 0], ls='None', marker=',', label=trigger_name, **plot_args)
    
        if (DY == 0).sum() > 0:
    
            ax1.errorbar(median[DY == 0], Y[DY == 0],
                         xerr=[median[DY == 0] - start[DY == 0], stop[DY == 0] - median[DY == 0]],
                         yerr=[bar * Y[DY == 0], 0.0 * Y[DY == 0]], uplims=True, ls='None', marker='', 
                         mfc=color, mec=color, ecolor=color, label=None, **plot_args)
    
        all_mins.append(Y.min() / 10)
        all_maxs.append(Y.max() * 10)
        
        all_tmins.append(start.min())
        all_tmaxs.append(stop.max())
            
        if redshift > 0:
        
            ax1.set_xlabel('Rest-frame time (s)')
        
        else:
            
            ax1.set_xlabel('Time (s)')
        
        if flux_type == "PhotonFlux":
        
            ax1.set_ylabel(r'Flux (ph. cm$^{-2}$ s$^{-1}$)')
        
        elif flux_type == "flux":
            
            ax1.set_ylabel(r'Flux (erg cm$^{-2}$ s$^{-1}$)')
        
        ax1.set_xscale('symlog')
        ax1.set_yscale('log')
        
        if plot_photon_index:
            
            ph_err = time_resolved_results['photonIndexError']
            
            ph_err = np.core.defchararray.replace(ph_err, "n.a.(fixed)", "0", count=None)
            
            ax2.errorbar(median[DY > 0], time_resolved_results['photonIndex'][DY>0], 
                         xerr=[median[DY > 0] - start[DY > 0], stop[DY > 0] - median[DY > 0]],
                         yerr=np.array(ph_err[DY > 0], dtype=float),
                         fmt='.') 
        
            ax2.set_xlabel("Time since trigger (s)")
        
            fig.subplots_adjust(hspace=0)
        
    ax1.set_xlim(min(all_tmins), max(all_tmaxs))
    ax1.set_ylim(min(all_mins), max(all_maxs))
    
    return fig
