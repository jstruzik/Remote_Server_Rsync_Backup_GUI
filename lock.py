import os, re, sys, logging
from StaticGlobals import lockfile

class lock:
	def __init__(self, lf=lockfile, log=True):
		self.log = log
		if log:
			self.logger = logging.getLogger(__name__)
		self.lockfile = lf
	
	def acquire(self, checkOnly=False):
		if os.path.exists(self.lockfile) and os.path.isfile(self.lockfile):
			self.output("Lock file exists!", level=logging.ERROR)
			if self.process_Is_Running():			
				self.output("Process already running, quitting.")
				sys.exit(1)
			else:
				self.output("Old lock file exists.")
				self.output("Transferring latest log file to the USB's TOOLS partition.")
				self.transferLatestLog()
				self.output("Removing old lock file.")
				os.remove(self.lockfile)
		if not checkOnly:
			self.output("Creating lockfile.")
			os.system('touch ' + self.lockfile)

	def release(self):
		self.output("Releasing lockfile.")
		if os.path.exists(self.lockfile) and os.path.isfile(self.lockfile):
			os.remove(self.lockfile)
			self.output("Lockfile removed.")
		else:
			self.output("Lockfile doesn't exist!", level=logging.ERROR)
			sys.exit(1)

	def transferLatestLog(self):
		logs = sorted( [ f for f in os.listdir('/tmp/') if re.match(".*_oitbackup_.*\.log", f) and os.path.isfile('/tmp/' + f) ], reverse=True )
		if len(logs) > 0:
			self.output("Copying: /tmp/" + logs[0] + " ==> /media/TOOLS/" + logs[0])
			os.system('cp /tmp/' + logs[0] + ' /media/TOOLS/' + logs[0])
		else:
			self.output("No previous logs found to transfer.")

	def process_Is_Running(self):
		pid = os.getpid()
		print pid
		ppid = os.getppid()
		print ppid
		# Change 'Main.py' to whatever the process is called when running
		command = 'ps x | grep "python Main.py" | grep -v grep | grep -v ' + str(pid) + ' | grep -v ' + str(ppid)
		if os.system( command ) != 256: #256 is returned if there is no output
			#So, it IS running
			return True
		else:
			return False
	
	def output(self, msg, level=logging.INFO):
		print msg
		if self.log:
			self.logger.log(level, msg)

if __name__ == "__main__":
	lk = lock(log=False)
	lk.acquire(checkOnly=True)
