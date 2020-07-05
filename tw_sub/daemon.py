# From "A simple unix/linux daemon in Python" by Sander Marechal 
# See http://stackoverflow.com/a/473702/1422096 and http://web.archive.org/web/20131017130434/http://www.jejik.com/articles/2007/02/a_simple_unix_linux_daemon_in_python/
#
# Modified to add quit() that allows to run some code before closing the daemon
# See http://stackoverflow.com/a/40423758/1422096
#
# Modified for Python 3 (see also: http://web.archive.org/web/20131017130434/http://www.jejik.com/files/examples/daemon3x.py)
#
# Joseph Ernest, 20200507_1220

import sys, os, time, atexit
from signal import signal, SIGTERM 

class Daemon:
	"""
	A generic daemon class.
	
	Usage: subclass the Daemon class and override the run() method
	"""
	def __init__(self, pidfile='_.pid', stdin='/dev/null', stdout='/dev/null', stderr='/dev/null'):
		self.stdin = stdin
		self.stdout = stdout
		self.stderr = stderr
		self.pidfile = pidfile
	
	def daemonize(self):
		atexit.register(self.onstop)
		signal(SIGTERM, lambda signum, stack_frame: exit())
        
		# write pidfile        
		pid = str(os.getpid())
		open(self.pidfile,'w+').write("%s\n" % pid)
	
	def onstop(self):
		self.quit()
		os.remove(self.pidfile)

	def start(self):
		"""
		Start the daemon
		"""
		# Check for a pidfile to see if the daemon already runs
		try:
			pf = open(self.pidfile,'r')
			pid = int(pf.read().strip())
			pf.close()
		except IOError:
			pid = None
	
		if pid:
			message = "pidfile %s already exist. Daemon already running?\n"
			sys.stderr.write(message % self.pidfile)
			sys.exit(1)
		
		# Start the daemon
		self.daemonize()
		self.run()

	def stop(self):
		"""
		Stop the daemon
		"""
		# Get the pid from the pidfile
		try:
			pf = open(self.pidfile,'r')
			pid = int(pf.read().strip())
			pf.close()
		except IOError:
			pid = None
	
		if not pid:
			message = "pidfile %s does not exist. Daemon not running?\n"
			sys.stderr.write(message % self.pidfile)
			return # not an error in a restart

		# Try killing the daemon process	
		try:
			while 1:
				os.kill(pid, SIGTERM)
				time.sleep(0.1)
		except OSError as err:
			err = str(err)
			if err.find("No such process") > 0:
				if os.path.exists(self.pidfile):
					os.remove(self.pidfile)
			else:
				print(str(err))
				sys.exit(1)

	def run(self):
		"""
		You should override this method when you subclass Daemon. It will be called after the process has been
		daemonized by start() or restart().
		"""

	def quit(self):
		"""
		You should override this method when you subclass Daemon. It will be called before the process is stopped.
		"""