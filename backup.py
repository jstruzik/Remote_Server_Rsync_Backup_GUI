import sys, os, subprocess,re,threading,copy,logging
from time import sleep
from StaticGlobals import REMOTE_PATH, gladeFile, REMOTE_BACKUP_SERVER
from remoteBackup import RemoteBackup
from rsyncFilterClass import rsyncfilter
from time import time

#Our infamously* glorious backup class
class backup:
	def __init__(self, appointment_number,  paths_to_backup, username, use_filter=True, password=None,
				backup_server = REMOTE_BACKUP_SERVER, remote_path_arg = REMOTE_PATH, gui_enabled = False):
		self.logger = logging.getLogger(__name__)
		self.rsync = {
			'exe' : '/usr/bin/rsync',
			'options' : '-rtvvhmi8Pl',
			'paths_to_backup' : paths_to_backup,
			'external_path' : False,
			'local_mountpoint' : '/home/liveuser/Desktop//',
			'log' : '/tmp/' + appointment_number + '.log',
			'server' : backup_server,
			'username' : username,
			'password' : password,
			'remote_path' : remote_path_arg,
			'use_filter' : use_filter,
			'generated_excludes' : '/rsync-excludes',
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
	
	def error(self, warning_message):
		warning = self.warn(warning_message);
		warning.run()

	def setAppointmentNumber(self, ap):
		self.logger.debug("Setting appointment number.")
		self.rsync['appointment_number'] = ap
		self.rsync['log'] = '/tmp/' + ap + '.log'
		return self
	
	def setUserName(self, user):
		self.logger.debug("Setting user name.")
		self.rsync['username'] = user
		return self
	
	def setPassword(self, pw):
		self.logger.debug("Setting password.")
		self.rsync['password'] = pw
		return self
	
	def setPathsToBackup(self, paths):
		self.logger.debug("Setting paths to backup.")
		self.rsync['paths_to_backup'] = paths
		return self
	
	def setUseFilter(self, use_filter):
		self.logger.debug("Setting filter toggle.")
		self.rsync['use_filter'] = use_filter
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

		self.logger.debug("Generating excludes file.")
		#Creates the filter object that will generate the excludes file.
		our_filter = rsyncfilter( self.rsync[ 'generated_excludes' ] )
		
		#Check to see if the backup will use a filter.
		if self.rsync[ 'use_filter' ] == True:
			#Now that we have a proper excludes file, we'll write it to disk.
			command.extend( ['--exclude-from="' + self.rsync[ 'generated_excludes' ] + '"' ] )		

		#Adds the current path to the backup
		if type(self.rsync['paths_to_backup']).__name__ == 'str':
			final = str(re.escape(self.rsync['paths_to_backup']))
			our_filter.add(final)
			#command.extend([final])
		else:
			for path in self.rsync['paths_to_backup']:
				our_filter.add( str(re.escape( path ) ) )
		
		#Writes the excludes file to disk and makes all the excludes case insensitive
		our_filter.out()
		
		if self.gui_enabled:
			self.logger.debug("Creating new progress window.")
			#Creates a new progress window
			self.progress_window = self.progress(self.coordsx,self.coordsy,gladeFile)
			self.progress_window.PULSE = True
			self.progress_window.run()
		else:
			self.progress_window = None

		if not self.rsync['external_path']:
			self.logger.debug("This will be a backup-server job.")
			#Adds the part of the command which specifies the backup server.
			self.rsync[ 'remote_path' ] = self.escapeQuotesInPath( self.rsync[ 'remote_path' ] ) + '/'
			self.backup_server()
		else:
			self.logger.debug("This will be a 'local' backup job.")
			if self.gui_enabled:
				#Creates a new progress window
				self.progress_window.local = True
			
			#Adds the path of the command which specifies the (external) backup location.
			r_path = self.rsync[ 'remote_path' ]
			self.rsync[ 'final_path' ] = r_path + 'Backups-' + self.rsync['appointment_number']+ '/' 
			self.rsync[ 'final_path' ] = self.escapeQuotesInPath( self.rsync[ 'final_path' ] )
			
			#Spawn a new thread
			self.logger.debug("Spawning new thread for local backup.")
			lbup = threading.Thread(target = self.backup_local, args=(command, self.progress_window,self.rsync['paths_to_backup'],self.rsync[ 'final_path' ]))
			self.logger.debug("Starting thread.")
			lbup.start()
			
			if self.gui_enabled:
				#Pass the thread to the progress window
				self.progress_window.set_current_thread(lbup)
			
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
	
	def backup_server(self):
			# Build a list of paths to backup
			paths_to_backup = []
			for path in self.rsync['paths_to_backup']:
				paths_to_backup.append( self.escapeQuotesInPath( path ) )
				
			if self.gui_enabled:
				self.logger.debug("Creating 'warn' object.")
				# Make a 'warn' object to pass to the remoteBackup class to use for error notification
				warnToPass = self.warn("msg")
			
				#Generates the textbuffer log to be put in the textview of tab "output"
				logwindow = self.gtk.TextBuffer(None)
				self.textview.set_buffer(logwindow)
			else:
				warnToPass = None
				self.textview = None

			# Make a new RemoteBackup object with the specified parameters
			self.logger.debug("Creating new RemoteBackup object for backup-server job.")
			rbackup = RemoteBackup( backupHost=self.rsync['server'],
									user=self.rsync['username'],
									password=self.rsync['password'], 
									apnumber=self.rsync['appointment_number'], 
									remotePath=self.rsync['remote_path'], 
									rsyncPaths=paths_to_backup, 
									warnObj=warnToPass, 
									logWindow=self.textview, 
									progressWindow=self.progress_window,
									useFilter=self.rsync['use_filter'],
									isBackup=True )
			
			# Start the new backup thread
			self.logger.debug("Starting remote backup thread.")
			rbackup.start()
			if self.gui_enabled:
				self.progress_window.set_current_thread(rbackup)
			
			##os.system("aplay sound.wav")
						
	def backup_local(self, command, pwindow,backup_paths,remote_path):	
		if self.gui_enabled:
			#Build our log window
			self.logger.debug("Building log window for local backup.")
			logwindow = self.gtk.TextBuffer(None)
			self.textview.set_buffer(logwindow)
		
		#Check if it's one folder or multiple. There's got to be an easier way to do this, I'm just braindead atm.
		if type(backup_paths).__name__ == 'str':
			self.logger.debug("Only one folder to backup.")
			command.extend(['"'+backup_paths+'"'])
			command.extend(['"'+remote_path+'"'])
			toUse = ' '.join(command)
			try:
				#Run our command
				self.logger.debug("Trying to subprocess the local backup command.")
				p = subprocess.Popen(toUse, shell=True, stdout = subprocess.PIPE, stderr = subprocess.STDOUT, close_fds=True)		
				
				while True:
					#Read each line in real-time
					line = p.stdout.readline()
					if not line: break
					
					#If we hit an rsync error in the output, error.
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
		
		#Multiple folders		
		else:
			self.logger.debug("Local backup - multiple folders.")
			default_command = copy.deepcopy(command)
			for path in backup_paths:
				command = copy.deepcopy(default_command)
				self.log("Path being backed up: " + path)
				command.extend(['"'+path+'"'])
				command.extend(['"'+remote_path+'"'])
				toUse = ' '.join(command)
				self.log("Using command: " + toUse)
				try:
					#Run our command
					self.logger.debug("Trying to subprocess local backup command (multiple folders).")
					p = subprocess.Popen(toUse, shell=True, stdout = subprocess.PIPE,stderr = subprocess.STDOUT, close_fds=True)
					
					#Iterate through each line
					while True:
						line = p.stdout.readline()
						if not line: break
						
						#If we hit a rsync error, pop up a warning but continue process.
						if "rsync error" in line:
							self.log( "Rsync error: " + line, level='error')
							
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
