#!/usr/bin/python
import corr, time, struct, sys, logging, pylab, os
import numpy as nm
from optparse import OptionParser
import scio,spifpga


#=======================================================================
def exit_fail(lh):
	print 'FAILURE DETECTED. Log entries:\n',lh.printMessages()
	try:
		fpga.stop()
	except: pass
	raise
	exit()

#=======================================================================
def channel_callback(option, opt, value, parser):
        """Deal with user-specified ADC channel selection in the option parser."""
        setattr(parser.values, option.dest, [int(v) for v in value.split(',')])
        return

#=======================================================================
def initialize_snap(snap_ip, opts, timeout=10, loglevel=20):
        """Connect to SNAP board, configure settings"""

        # Set up SNAP logger
        lh = corr.log_handlers.DebugLogHandler()
        logger = logging.getLogger(snap_ip)
        logger.addHandler(lh)
        logger.setLevel(loglevel)

        # Connect to the SNAP board configure spectrometer settings
        logger.info('Connecting to server %s on port %i... '%(snap_ip, opts.port))
        fpga = corr.katcp_wrapper.FpgaClient(snap_ip, opts.port, timeout=timeout, logger=logger)
        time.sleep(1)

        if fpga.is_connected():
	        logger.info('Connected!')
        else:
	        logger.error('ERROR connecting to %s on port %i.' %(snap,opts.port))
	        exit_fail()

        logger.info('Configuring accumulation period...')
        fpga.write_int('acc_len', opts.acc_len)
        fpga.write_int('fft_shift', 0xFFFFFFFF)
        logger.info('Done configuring')

        time.sleep(2)

        return fpga

#=======================================================================
def get_tail(mylist):
	#data get appended to the end of a list of lists
	#for writing, pull the tail ends and return as an array that can be written
	tmp=[]
	for ii in mylist:
		tmp.append(ii[-1])
	return nm.array(tmp)

#=======================================================================
def acquire_data(fpga, opts, ndat=4096, nbit=8, wait_for_new=True):

	if opts.sim is None:
		try:
			regdict=spifpga.read_core_info('core_info.tab')
			fd=spifpga.config_spi()
			if (fd<0):
				print 'configuration failure in spifpga.  reverting to slower read'
				read_fast=False
			read_fast=True
		except:
			read_fast=False
        # ACQUIRE ALL THE DATAS!!!!
        while True:

                # Get current time stamp and use that for the output directory
                tstart = time.time()
		if (tstart>1e5):
			tfrag=repr(tstart)[:5]
		else:
			print 'warning in acquire_data - tstart seems to be near zero.  Did you set your clock?'
			tfrag='00000'
		#outsubdir = opts.outdir+'/'+str(tstart)
		outsubdir = opts.outdir+'/'+tfrag +'/' + str(tstart)
                os.makedirs(outsubdir)
                logging.info('Writing current data to %s' %(outsubdir))

                # Initialize data arrays
                nchan = len(opts.channel)
                timestamps1 = []
                timestamps2 = []
                fft_shift = []
                fft_of_cnt = []
                acc_cnt1 = []
                acc_cnt2 = []
                sys_clk1 = []
                sys_clk2 = []
                sync_cnt1 = []
                sync_cnt2 = []
                aa = [[] for i in range(nchan)]
                bb = [[] for i in range(nchan)]
                ab_real = [[] for i in range(nchan)]
                ab_imag = [[] for i in range(nchan)]

                # Open raw files for scio
		f_timestamp1 = open(outsubdir+'/time_start.raw','w')
		f_timestamp2 = open(outsubdir+'/time_stop.raw','w')
		f_fft_shift = open(outsubdir+'/fft_shift.raw','w')
		f_fft_of_cnt = open(outsubdir+'/fft_of_cnt.raw','w')
		f_acc_cnt1 = open(outsubdir+'/acc_cnt1.raw','w')
		f_acc_cnt2 = open(outsubdir+'/acc_cnt2.raw','w')
		f_sys_clk1 = open(outsubdir+'/sys_clk1.raw','w')
		f_sys_clk2 = open(outsubdir+'/sys_clk2.raw','w')
		f_sync_cnt1 = open(outsubdir+'/sync_cnt1.raw','w')
		f_sync_cnt2 = open(outsubdir+'/sync_cnt2.raw','w')
		f_aa=scio.scio(outsubdir+'/aa.scio')
		f_bb=scio.scio(outsubdir+'/bb.scio')
		f_ab_real=scio.scio(outsubdir+'/ab_real.scio')
		f_ab_imag=scio.scio(outsubdir+'/ab_imag.scio')
                # Save data in this subdirectory for specified time length
                while time.time()-tstart < opts.tfile*60:

                        # Wait for a new accumulation if we're reading
                        # from the FPGA
                        if wait_for_new and opts.sim is None:
                                acc_cnt_old = fpga.read_int('acc_cnt')
                                while True:
                                        acc_cnt_new = fpga.read_int('acc_cnt')
                                        # Ryan's paranoia: avoid possible reinitialization
                                        # crap from first spectrum accumulation
                                        if acc_cnt_new >= acc_cnt_old + 2:
                                                break
                                        time.sleep(0.1)

                        # Time stamp at beginning of read commands.
                        # Reading takes a long time (and there are
                        # sometimes timeouts), so keep track of time
                        # stamps for both start and end of reads.
                        t1 = time.time()
                        timestamps1.append(t1)
                        
                        # Read data from the actual SNAP board...
                        if opts.sim is None:

                                # Start with housekeeping registers
                                acc_cnt1.append( acc_cnt_new )
                                fft_shift.append( fpga.read_uint('fft_shift') )
                                fft_of_cnt.append( fpga.read_int('fft_of_cnt') )
                                sys_clk1.append( fpga.read_int('sys_clkcounter') )
                                sync_cnt1.append( fpga.read_int('sync_cnt') )

                                # Now read the actual data
                                for ic,c in enumerate(opts.channel):
                                        field = 'pol'+str(c)+'a'+str(c)+'a_snap'
                                        #val = nm.array(struct.unpack('>'+str(ndat)+'Q', fpga.read(field,ndat*nbit,0)))
					val=spifpga.read_register(field,fd,regdict,'uint64')
                                        aa[ic].append(val)

                                        field = 'pol'+str(c)+'b'+str(c)+'b_snap'
                                        #val = nm.array(struct.unpack('>'+str(ndat)+'Q', fpga.read(field,ndat*nbit,0)))
					val=spifpga.read_register(field,fd,regdict,'uint64')
                                        bb[ic].append(val)

                                        field = 'pol'+str(c)+'a'+str(c)+'b_snap_real'
                                        #val = nm.array(struct.unpack('>'+str(ndat)+'q', fpga.read(field,ndat*nbit,0)))
					val=spifpga.read_register(field,fd,regdict,'int64')
                                        ab_real[ic].append(val)

                                        field = 'pol'+str(c)+'a'+str(c)+'b_snap_imag'
                                        #val = nm.array(struct.unpack('>'+str(ndat)+'q', fpga.read(field,ndat*nbit,0)))
					val=spifpga.read_register(field,fd,regdict,'int64')
                                        ab_imag[ic].append(val)
                                        
                                # Check that new accumulation hasn't started during
                                # the previous read commands
                                acc_cnt_end = fpga.read_int('acc_cnt')
                                if acc_cnt_new != acc_cnt_end:
                                        logging.warning('Accumulation changed during data read')
                                acc_cnt2.append( acc_cnt_end )
                                sys_clk2.append( fpga.read_int('sys_clkcounter') )
                                sync_cnt2.append( fpga.read_int('sync_cnt') )
                                        
                        # ...or generate random numbers for testing purposes
                        else:
                                fft_shift.append( nm.random.random(1) )
                                fft_of_cnt.append( nm.random.random(1) )
                                acc_cnt1.append( nm.random.random(1) )
                                acc_cnt2.append( nm.random.random(1) )
                                sys_clk1.append( nm.random.random(1) )
                                sys_clk2.append( nm.random.random(1) )
                                sync_cnt1.append( nm.random.random(1) )
                                sync_cnt2.append( nm.random.random(1) )
                                for ic,c in enumerate(opts.channel):
                                        aa[ic].append( nm.random.random(ndat)*(ic+1) )
                                        bb[ic].append( nm.random.random(ndat)*(ic+1) )
                                        ab_real[ic].append( nm.random.random(ndat)*(ic+1) )
                                        ab_imag[ic].append( nm.random.random(ndat)*(ic+1) )

                        # Time stamp again after read commands are finished
                        t2 = time.time()
                        timestamps2.append(t2)
                        
                        # Write data with scio -- append to files
			nm.array(timestamps1[-1]).tofile(f_timestamp1)
			nm.array(timestamps2[-1]).tofile(f_timestamp2)
			nm.array(fft_shift[-1]).tofile(f_fft_shift)
			nm.array(fft_of_cnt[-1]).tofile(f_fft_of_cnt)
			nm.array(acc_cnt1[-1]).tofile(f_acc_cnt1)
			nm.array(acc_cnt2[-1]).tofile(f_acc_cnt2)
			nm.array(sys_clk1[-1]).tofile(f_sys_clk1)
			nm.array(sys_clk2[-1]).tofile(f_sys_clk2)
			nm.array(sync_cnt1[-1]).tofile(f_sync_cnt1)
			nm.array(sync_cnt2[-1]).tofile(f_sync_cnt2)
			f_timestamp1.flush()
			f_timestamp2.flush()
			f_fft_shift.flush()
			f_fft_of_cnt.flush()
			f_acc_cnt1.flush()
			f_acc_cnt2.flush()
			f_sys_clk1.flush()
			f_sys_clk2.flush()
			f_sync_cnt1.flush()
			f_sync_cnt2.flush()
			
			#scio.append(get_tail(aa),outsubdir+'/aa.scio')
			#scio.append(get_tail(bb),outsubdir+'/bb.scio')
			#scio.append(get_tail(ab_real),outsubdir+'/ab_real.scio')
			#scio.append(get_tail(ab_imag),outsubdir+'/ab_imag.scio')
			f_aa.append(get_tail(aa))
			f_bb.append(get_tail(bb))
			f_ab_real.append(get_tail(ab_real))
			f_ab_imag.append(get_tail(ab_imag))


			time.sleep(opts.wait)

                # End while loop over file chunk size

                # As a backup, write data to numpy files (should get
                # rid of this after testing).  This dumps just once at
                # the end of every chunk.
                nm.save(outsubdir+'/time_start.npy', nm.asarray(timestamps1))
                nm.save(outsubdir+'/time_stop.npy', nm.asarray(timestamps2))
                nm.save(outsubdir+'/fft_shift.npy', nm.asarray(fft_shift))
                nm.save(outsubdir+'/fft_of_cnt.npy', nm.asarray(fft_of_cnt))
                nm.save(outsubdir+'/acc_cnt1.npy', nm.asarray(acc_cnt1))
                nm.save(outsubdir+'/acc_cnt2.npy', nm.asarray(acc_cnt2))
                nm.save(outsubdir+'/sys_clk1.npy', nm.asarray(sys_clk1))
                nm.save(outsubdir+'/sys_clk2.npy', nm.asarray(sys_clk2))
                nm.save(outsubdir+'/sync_cnt1.npy', nm.asarray(sync_cnt1))
                nm.save(outsubdir+'/sync_cnt2.npy', nm.asarray(sync_cnt2))
                nm.save(outsubdir+'/aa.npy', nm.asarray(aa))
                nm.save(outsubdir+'/bb.npy', nm.asarray(bb))
                nm.save(outsubdir+'/ab_real.npy', nm.asarray(ab_real))
                nm.save(outsubdir+'/ab_imag.npy', nm.asarray(ab_imag))

        # End infinite loop

	return
        
#=======================================================================
if __name__ == '__main__':

        # Parse options
	parser = OptionParser()
	parser.set_usage('snap_daq.py <SNAP_HOSTNAME_or_IP> [options]')
	parser.set_description(__doc__)
	parser.add_option('-o', '--outdir', dest='outdir',type='str', default='/data/snap/raw',
		          help='Output directory [default: %default]')
	parser.add_option('-l', '--logdir', dest='logdir',type='str', default='/data/snap/log',
		          help='Log directory [default: %default]')
	parser.add_option('-p', '--port', dest='port',type='int', default=7147,
		          help='Port number [default: %default]')
	parser.add_option('-c', '--channel', dest='channel',type='string', default=[0,1],
		          help='ADC channels as comma separated list [default: %default]',
                          action='callback', callback=channel_callback)
	parser.add_option('-a', '--acc_len', dest='acc_len', type='int',default=2*(2**28)/2048,
		          help='Number of vectors to accumulate between dumps [default: %default]')
	parser.add_option('-t', '--tfile', dest='tfile', type='int',default=15,
		          help='Number of minutes of data in each file subdirectory [default: %default]')
	parser.add_option('-w', '--wait', dest='wait', type='int',default=0,
		          help='Number of seconds to wait between taking spectra [default: %default]')
	parser.add_option('-s', '--sim', dest='sim', action='store_true',
		          help='Simulate incoming data [default: %default]')
	parser.add_option('-C','--comment',dest='comment',type='str',default='',help='Comment for log')
	opts, args = parser.parse_args(sys.argv[1:])

	#print ' comment is ' + opts.comment
	#print type(opts.comment)
	#print len(opts.comment)
	#assert(1==0)
	if args==[]:
                if opts.sim is None:
		        print 'Please specify a SNAP board. Run with the -h flag to see all options.\nExiting.'
		        exit()
	else:
		snap_ip = args[0]

        #--------------------------------------------------------------

        # Create log file
        if not os.path.exists(opts.logdir):
                os.makedirs(opts.logdir)
                print 'Created directory',opts.logdir
        logging.basicConfig(level=logging.DEBUG,
                            format='%(asctime)s %(name)-12s %(message)s',
                            datefmt='%m-%d %H:%M',
                            filename=opts.logdir+'/'+str(time.time())+'.log',
                            filemode='w')
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        formatter = logging.Formatter('%(name)-12s: %(message)s')
        console.setFormatter(formatter)
        logging.getLogger('').addHandler(console)

        # Save run-time options to file
        logging.info('======= Run-time options =======')
        logging.info('ADC channel selection: %s' %(opts.channel))
        logging.info('Accumulate length: %d' %(opts.acc_len))
        logging.info('Minutes per file: %d' %(opts.tfile))
        logging.info('Seconds between spectra: %d' %(opts.wait))
        logging.info('Simulation mode: %s' %(opts.sim))
	logging.info('Comment: %s' % (opts.comment))
        logging.info('================================')

        # Connect to SNAP board and initialize if not in sim mode
        fpga = None
        if opts.sim is None:
                fpga = initialize_snap(snap_ip, opts)

        # Acquire data
        logging.info('Writing data to top level location %s' %(opts.outdir))
        if not os.path.exists(opts.outdir):
                os.makedirs(opts.outdir)
                print 'Created directory', opts.outdir
	try:
		acquire_data(fpga, opts)
	finally:
		logging.info('Terminating DAQ script at %s' % str(time.time()))
