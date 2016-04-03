Collection of routines for taking/writing/reading data for scihi.
After cloning, you will need to compile Jack's spifpga_user.c into 
a shared library.  A command almost guaranteed to work is:
gcc -std=c99 -O3 -shared -fPIC -o libspifpga_user.so spifpga_user.c 

The scihi module will let you read data.  You can read the last
15 minutes of data with:
dat=scihi.read_data_by_ctime(time.time()-900,dr='tmp/raw')
where dr is set to be whever the archive is.  Its default value should
work for the pi.  The second argument into scihi.read_data_by_ctime is an 
optional stopping time.  If absent, it reads up to the current time.
