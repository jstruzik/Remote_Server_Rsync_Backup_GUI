import sys, os, subprocess,re,threading,logging
from time import sleep
from StaticGlobals import REMOTE_PATH, gladeFile, REMOTE_BACKUP_SERVER
from remoteBackup import RemoteBackup
from rsyncFilterClass import rsyncfilter

class restore:
	def __init__(self, appointment_number, path_to_restore_to, username, password=None,
				backup_server=REMOTE_BACKUP_SERVER, remote_path_arg = REMOTE_PATH, gui_enabled = False):
		self.logger = logging.getLogger(__name__)
		self.rsync = {
			'exe' : '/usr/bin/rsync',
			'options' : '-rtvvhmi8Pl',
			'external_path' : False,
			'path_to_restore_to' : path_to_restore_to,
			'log' : '/tmp/' + appointment_number + '_restore.log',
			'server' : backup_server,
			'username' : username,
			'password' :password,
			'remote_path' : remote_path_arg,
			'appointment_number' : appointment_number,
			'process_id' : None
			}
		self.setGuiEnabled(gui_enabled)
		self.logger.debug("Initialized.")
			
	def setGuiEnabled(self, enabled):
		self.logger.debug("Configuring gui.")
		if enabled:
			self.logger.debug("Enabling gui.")
			try:
				self.gtk = __import__('gtk')
				self.gobject = __import__('gobject')
			except:
				sys.exit("GTK/Glade not found!")
			self.warn = __import__('warning').warn
			self.progress = __import__('progressBar').progress
			self.logger.debug("Gui enabled.")
		self.gui_enabled = enabled
		return self
	
	def error (self, warning_message):
		warning = self.warn(warning_message);
		warning.run()
	
	def setAppointmentNumber(self, ap):
		self.logger.debug("Setting appointment number.")
		self.rsync['appointment_number'] = ap
		self.rsync['log'] = '/tmp/' + ap + '_restore.log'
		return self
	
	def setUserName(self, user):
		self.logger.debug("Setting user name.")
		self.rsync['username'] = user
		return self
	
	def setPassword(self, pw):
		self.logger.debug("Setting password.")
		self.rsync['password'] = pw
		return self
	
	def setPathsToRestoreTo(self, path):
		self.logger.debug("Setting paths to restore to.")
		self.rsync['paths_to_restore_to'] = path
		return self
	
	def setBackupServer(self, backup_server):
		self.logger.debug("Setting backup server.")
		self.rsync['server'] = backup_server
		return self
	
	def setRemotePath(self, rpath):
		self.logger.debug("Setting remote path.")
		self.rsync['remote_path'] = rpath
		return self

	def run(self):
		self.logger.info("Running.")
		if self.rsync[ 'remote_path' ] != REMOTE_PATH:
			self.rsync[ 'external_path' ] = True

		#Our rsync command
		command = [ self.rsync[ 'exe' ], self.rsync[ 'options' ], '--stats', '--log-file="' + self.rsync[ 'log' ] + '"' ]
		
		#If local restoration
		if self.rsync[ 'external_path' ]:
			#Adds the part of the command which specifies the alternative location to pull from
			path_restoring_from = self.escapeQuotesInPath( self.rsync[ 'remote_path' ] )
			#command.extend( [ path ] )
			
		path = self.escapeQuotesInPath( self.rsync[ 'path_to_restore_to' ] )
		path += "/Backups-"+self.rsync['appointment_number']

		#Adds the current path to the backup			
		#command.extend( [ path ] )

		if not os.path.isdir(path):
			self.logger.debug("%s is not a folder, creating it." % path)
			self.log("Creating directory: %s" % path)
			mkdir_ID = os.system( "mkdir -p " + path )
			if mkdir_ID != 0:
				self.log("Something awful happened trying to create the restore point.", level='error')
				self.log("Check that you can access it first before trying again and check permissions.", level='error')
				self.gobject.idle_add(self.error, "Could not make the restore point - check log for details.")
				raise OSError("Could not make the restore point.")

		#This puts the command into a single string, instead of its current "list" form. (fixed this to use join() instead of a for loop)
		#self.toUse = ' '.join(command)

		if self.gui_enabled:
			#Creates a new progress window
			self.logger.debug("Create a new progress window.")
			self.progress_window = self.progress(self.coordsx,self.coordsy,gladeFile)
			self.progress_window.PULSE = True
			self.progress_window.run()
		else:
			self.progress_window = None

		#Rsync to server
		if not self.rsync[ 'external_path' ]:
			self.logger.debug("Restoring from server.")
			self.restore_server(path)
		else:
			self.logger.debug("Restoring from local path.")
			if self.gui_enabled:
				#Creates our progress window
				self.progress_window.local = True
			self.logger.debug("Creating thread for local restore.")
			lres = threading.Thread(target = self.restore_local, args=(command, self.progress_window,path_restoring_from,path))
			self.logger.debug("Starting local restore thread.")
			lres.start()
			if self.gui_enabled:
				self.progress_window.set_current_thread(lres)
			
	def set_log_window(self,log):
		self.textview = log
	
	def set_window_coordinates(self,coordsx,coordsy):
		self.coordsx = coordsx
		self.coordsy = coordsy
	
	def log(self, text, level=logging.INFO, stream=False):
		if level != logging.INFO:
			loglevel = getattr(logging, level.upper(), None)
			if not isinstance(loglevel, int):
				raise ValueError('Invalid log level: %s' % level)
			level = loglevel
		# Print text to console normally if it is being streamed
		if stream:
			print text
		else: # otherwise, let the logger print it to console
			self.logger.log(level, text)
		if text[-1] != '\n':
			text += '\n'
		if self.gui_enabled:
			self.gobject.idle_add(self.logToGui, text)
	
	def logToGui(self, text):
		# Append it to the end of the logwindow (at the end_iter location)
		self.textview.get_buffer().insert(self.textview.get_buffer().get_end_iter(), text)
		# Scroll the logwindow the the end
		self.textview.scroll_mark_onscreen(self.textview.get_buffer().get_insert())
	
	def restore_server(self, localPath):
		pathToRestoreTo = localPath
		
		if self.gui_enabled:
			# Make a 'warn' object to pass to the remoteBackup class to use for error notification
			self.logger.debug("Creating 'warn' object.")
			warnToPass = self.warn("msg")
			
			#Generates the textbuffer log to be put in the textview of tab "output"
			logwindow = self.gtk.TextBuffer(None)
			self.textview.set_buffer(logwindow)
		else:
			warnToPass = None
			self.textview = None
		
		# Make a new RemoteBackup object with the specified parameters
		self.logger.debug("Creating RemoteBackup object for remote restore.")
		rrestore = RemoteBackup( backupHost=self.rsync['server'],
								user=self.rsync['username'], 
								password=self.rsync['password'], 
								apnumber=self.rsync['appointment_number'], 
								remotePath=self.rsync['remote_path'], 
								rsyncPaths=pathToRestoreTo, 
								warnObj= warnToPass, 
								logWindow=self.textview,
								progressWindow=self.progress_window,
								useFilter=False,
								isBackup=False )
		
		# Set up the backup running in a new thread
		#bup = threading.Thread(target = rrestore.runRestore) #, args=(self.progress_window,))#the comma is NOT a typo, check python tuple doc

		# Start the new restore thread
		self.logger.debug("Starting remote restore thread.")
		rrestore.start()
		if self.gui_enabled:
			self.progress_window.set_current_thread(rrestore)

		##os.system("aplay sound.wav")
	
	def restore_local(self, command, pwindow,path_restoring_from,path_restoring_to):
		count = 0.000
		percent = 0.000
		if self.gui_enabled:
			self.logger.debug("Building log window for local restore.")
			logwindow = self.gtk.TextBuffer(None)
			self.textview.set_buffer(logwindow)
		#Run local restore command
		if type(path_restoring_from).__name__ == 'str':
			self.logger.debug("Only one path to restore from.")
			command.extend(['"'+path_restoring_from+'"'])
			command.extend(['"'+path_restoring_to+'"'])
			try:
				self.logger.debug("Trying to subprocess the local restore command.")
				p = subprocess.Popen(' '.join(command), shell=True, stdout = subprocess.PIPE, close_fds=True)
				while True:
					line = p.stdout.readline()
					if not line: break
					if "rsync error" in line:
						self.log("Rsync error: " + line, level='error')
					self.log(line, stream=True)
						
				#Command completed
				(stdout, stderr) = p.communicate()
				
			except OSError, e:
				self.log("Rsync did not finish correctly!", level='error')
				if self.gui_enabled:
					pwindow.destroy()
					self.gobject.idle_add(self.error,"Rsync did not finish correctly!")
			except ValueError, e:
				self.log("Rsync did not finish correctly!", level='error')
				if self.gui_enabled:
					pwindow.destroy()
					self.gobject.idle_add(self.error,"Rsync did not finish correctly!")
		else:
			self.logger.debug("Local restore - multiple folders.")
			for path in path_restoring_from:
				command.extend(['"'+path+'"'])
				command.extend(['"'+path_restoring_to+'"'])
				try:
					self.logger.debug("Trying to subprocess local restore command (multiple folders)")
					p = subprocess.Popen(' '.join(command), shell=True, stdout = subprocess.PIPE, close_fds=True)
					#For each line read in the rsync command (since rsync cannot pass its file list)
					##line = p.stdout.readline()
					while True:
						line = p.stdout.readline()
						if not line: break
						if "rsync error" in line:
							self.log("Rsync error: " + line, level='error')
						self.log(line, stream=True)

					#Command completed
					(stdout, stderr) = p.communicate()
				except OSError, e:
					self.log("Rsync did not finish correctly!", level='error')
					if self.gui_enabled:
						pwindow.destroy()
						self.gobject.idle_add(self.error,"Rsync did not finish correctly!")
				except ValueError, e:
					self.log("Rsync did not finish correctly!", level='error')
					if self.gui_enabled:
						pwindow.destroy()
						self.gobject.idle_add(self.error,"Rsync did not finish correctly!")
		if self.gui_enabled:
			pwindow.complete()
		
	def escapeQuotesInPath( self,path ):
		#Remove the trailing slash from path if it has one
		if path[-1] == "/":
			path = path[0:-1]
		if "\"" in path:
			if path[0] == "\"":
				path = path[1:]
			if path[-1] == "\"":
				path = path[:-1]
			path = path.replace('"', '\\"') #Replace any occurences of " in a path with \" (excluding the first and last quotes)
			path = "\"" + path + "\"" #Put the first and last quotes back around the path....may be a better way to do this
		return path
