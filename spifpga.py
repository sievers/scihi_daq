#Python wrapper for Jack Hickish's spifpga C code for reading from/writing to 
#FPGAs.  Current functionality very limited, but read speed on large registers improved
#Requires spifpga_user be compiled into a shared library.
#spifpga_user can be compiled with something like: 
#  gcc -std=c99 -O3 -shared -fPIC -o libspifpga_user.so spifpga_user.c   
#Initial code by JLS, 31 Mar 2016


import numpy 
import ctypes

#gcc -I. -O3 -shared -o libspifpga_user.so spifpga_user.c 

try:
    mylib=ctypes.cdll.LoadLibrary("libspifpga_user.so")
except:
    mylib=ctypes.cdll.LoadLibrary("./libspifpga_user.so")


config_spi_c=mylib.config_spi
config_spi_c.restype=ctypes.c_int
config_spi_c.argtypes=[]

close_spi_c=mylib.close_spi
close_spi_c.argtypes=[ctypes.c_int]

bulk_read_c=mylib.bulk_read
bulk_read_c.argtypes=[ctypes.c_int,ctypes.c_uint, ctypes.c_uint,ctypes.c_void_p]
bulk_read_c.restype=ctypes.c_int
#int bulk_read(int fd, unsigned int start_addr, unsigned int n_bytes, unsigned int *buf)


def config_spi():
    return config_spi_c()

def close_spi(fd):
    close_spi_c(fd)


def read_register(regname,fd,regdict,mydtype):
    rw=regdict[regname][0]
    offset=regdict[regname][1]
    nbyte=regdict[regname][2]
    bytes_per_elem=0    
    if (mydtype[-2:]=='32'):
        bytes_per_elem=4
    if (mydtype[-2:]=='64'):
        bytes_per_elem=8
    if (bytes_per_elem==0):
        print 'unknown dtype ' + mydtype
        return None
    nelem=nbyte/bytes_per_elem
    vec=numpy.zeros(nelem,dtype=mydtype)
    isok=bulk_read_c(fd,offset,nbyte,vec.ctypes.data)
    #print 'isok is ' + repr(isok)
    if (isok==-1):
        print 'Error encountered in read_register'
        return None
    if (isok!=143):
        print "unexpected value returned by read_register " + repr(isok)
    return vec

def read_core_info(fname):
    f=open(fname,'r')
    lines=f.readlines()
    f.close()
    regdict={}
    for ll in lines:
        tags=ll.split()
        #print tags[0] + ' ' + tags[1] + ' ' + tags[2] + ' ' +tags[3]
        regdict[tags[0]]=[int('0x'+tags[1],0),int('0x'+tags[2],0),int('0x'+tags[3],0)]
    return regdict


