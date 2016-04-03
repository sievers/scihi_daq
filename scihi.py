import numpy
import scio
import glob
import time

regdict={}
regdict['aa.scio']='float64'
regdict['ab_real.scio']='float64'
regdict['ab_imag.scio']='float64'
regdict['bb.scio']='float64'
regdict['acc_cnt1.raw']='float64'
regdict['acc_cnt2.raw']='float64'
regdict['fft_of_cnt.raw']='float64'
regdict['fft_shift.raw']='float64'
regdict['sync_cnt1.raw']='float64'
regdict['sync_cnt2.raw']='float64'
regdict['sys_clk1.raw']='float64'
regdict['sys_clk2.raw']='float64'
regdict['time_start.raw']='float64'
regdict['time_stop.raw']='float64'



#aa=scihi.get_dirs(tt,time.time()-900,dr='tmp/raw')

def get_dirs(tstart,tstop=None,dr='/data/snap/raw/'):
    dirs=glob.glob(dr+'/?????')
    
    dd=numpy.zeros(len(dirs),dtype='int64')
    for ii in range(len(dirs)):
        tmp=dirs[ii].split('/')
        #print tmp[-1]
        dd[ii]=numpy.int(tmp[-1])
    
    #we'll check directories with possible starting ctimes
    #go one earlier since if tstart is just after the ctime
    #has ticked over into a new directory some data may
    #live in the previous directory
    dmin=numpy.int(str(tstart)[0:5])-1
    #print dmin
    dd=dd[dd>=dmin]
    if (tstop is None)==False:
        dmax=numpy.int(str(tstop)[0:5])
        dd=dd[dd<=dmax]
    #print dd
    alldirs=[]
    for mydir in dd:
        tmp=dr+'/'+str(mydir)+'/'+str(mydir)+'*'
        dirs=glob.glob(tmp)
        alldirs+=dirs
    #print alldirs
    ctimes=numpy.zeros(len(alldirs))
    
    for ii,mydir in enumerate(alldirs):
        ctimes[ii]=numpy.double(mydir.split('/')[-1])
    
    ct2=ctimes[ctimes<tstart]
    if len(ct2)>0:
        tmin=ct2.max()-1e-3
    else:
        tmin=tstart-1e-3

    inds=numpy.argsort(ctimes)
    #ctimes=ctimes[inds]
    #print ctimes-1459701000
    #alldirs=alldirs[inds]

    isok=ctimes>tmin
    if (tstop is None)==False:
        isok[ctimes>tstop]=False
    usedirs=[]
    for ii  in  range(len(inds)):
        if isok[inds[ii]]:
            usedirs.append(alldirs[inds[ii]])
    return usedirs



def read_channel_from_dirs(name,dirs,dtype='float64'):
    #assumes dirs is a list of directories that 
    #contain possibly useful data.  You probably want 
    #them sorted by ctime.
    crap=[None]*len(dirs)


    if name[-3:]=='npy':
        #read numpy arrays
        for ii,dr in enumerate(dirs):
            fname=dr+'/'+name
            crap[ii]=numpy.load(fname)
        #if reading data, make sure it comes back suitable stacked
        if len(crap[0].shape)==3:
            return numpy.hstack(crap)

        return numpy.hstack(crap)
    if name[-4:]=='scio':
        for ii,dr in enumerate(dirs):
            fname=dr+'/'+name
            crap[ii]=scio.read(fname)
        #print crap[0].shape
        crap=numpy.vstack(crap)
        return numpy.swapaxes(crap,0,1)
        
    #assume we have a raw type now


    for ii,dr in enumerate(dirs):
        fname=dr+'/'+name
        f=open(fname)
        crap[ii]=numpy.fromfile(f,dtype=dtype)
        f.close()
        #print crap[ii].shape
        #print type(crap[ii])
        
    return numpy.hstack(crap)

def read_data_by_ctime(tstart,tstop=None,dr='/data/snapraw/',mydict=regdict):
    dirs=get_dirs(tstart,tstop,dr)
    data={}
    for chan in mydict.keys():
        cc=chan.split('.')[0]
        data[cc]=read_channel_from_dirs(chan,dirs,dtype=mydict[chan])
    if tstop is None:
        isok=data['time_start']>tstart
    else:
        isok=(data['time_start']>=tstart)&(data['time_stop']<=tstop)

    for chan in data.keys():
        if len(data[chan].shape)==3:
            tmp=data[chan]
            
            data[chan]=data[chan][:,isok,:]
        if len(data[chan].shape)==2:
            data[chan]=data[chan][isok,:]
        if len(data[chan].shape)==1:
            data[chan]=data[chan][isok]
    return data
    
def read_data(tstart,tstop=None,dr='/data/snap/raw/',mydict=regdict,fmt='%Y%m%d_%H%M%S'):
    tstart=time.mktime(time.strptime(tstart,fmt))
    if (tstop is None)==False:
        tstop=time.mktime(time.strptime(tstop,fmt))
    return read_data_by_ctime(tstart,tstop,dr,mydict)
    


