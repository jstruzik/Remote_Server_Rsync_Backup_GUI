import sys, os, subprocess, paramiko, socket, re, errno, threading, logging
from time import sleep, time
from StaticGlobals import global_log_file

class RemoteBackup(threading.Thread):
	
	def __init__( self, backupHost, user, password, apnumber, remotePath, rsyncPaths, 
						warnObj=None, logWindow=None, progressWindow=None, useFilter=True, customFilter=None, isBackup=True ):
		"""Create a new RemoteBackup.
		     Required parameters:
				@param backupHost
					hostname or IP address of the backup server
				@param user
					user name to log into the backup server
				@param password
					password for supplied user name
				@param apnumber
					appointment number for the backup job
				@param remotePath
					path to the backup folder on the
					backup server
				@param rsyncPaths
					list of paths to back up on the live host 
					(machine to be backed up)
					
			Option parameters:
				@param warnObj
					(default:None) a 'warn' object supplied from
					'oitbackupgui' to show warning messages in a
					popup (RECOMMENDED)
				@param useFilter
					(default:True) boolean specifying whether we
					need to use a filter or not
				@param customFilter
					(default:None) path to the custom filter 
					file on the live host (machine to be backed up)
					
			Normal usage:
				- create a new RemoteBackup object (rb) with the
				  specified parameters
				- execute rb.runBackup() to begin 'batch' processing
				  each rsync path individually and start the backup
				  (this may be run in a separate thread)
		"""
		super(RemoteBackup, self).__init__()
		self.MASTER_FILTER		= "MasterFilter.excludes"
		self.ssh_key			= "id_rsa_reverse_backup"
		self.known_hosts_file 	= '/.ssh/known_hosts'
		self.backupHost			= backupHost
		self.username			= user
		self.password 			= password
		self.liveUser			= 'liveuser'
		self.ap					= apnumber
		self.warn				= warnObj
		self.isBackup			= isBackup
		self.terminate			= False
		self.terminate_complete = False
		self.connectionMade		= False
		self.progress_window	= None
		self.logwindow			= None
		self.cmd_channel		= None
		self.transport			= None
		self.sock				= None
		
		# Create a logger with the name of this module
		self.logger = logging.getLogger(__name__)
		
		if logWindow or progressWindow:
			self.gobject = __import__('gobject')
		if logWindow != None:
			self.gobject.idle_add(self.setLogWindow, logWindow )
		if progressWindow != None:
			self.gobject.idle_add(self.setProgressWindow, progressWindow )
		
		# Let's lookup the host's local IP address on the network
		self.lookupHost()
		
		# Let's initiate the SSH connection so that we can run remote commands
		self.initiateSSH()
		# We can now use self.ssh to access the ssh connection		
		
		# Set the path to backup to on the backup server
		self.backupPath = remotePath + str(self.ap) + '/'
		#self.backupPath = "/client/" + str(self.ap) + '/'
		
		# Set the log file path on the backup server
		self.logFile = self.backupPath + str(self.ap) + '.log'
		self.restoreLog = str(self.ap) + '-restore.log'
		self.restoreLogFull = self.backupPath + self.restoreLog
		
		# Save the rsync arguments to use
		#if type(rsyncArgs).__name__ == 'list':
		#	self.rsyncArgs = rsyncArgs
		#elif type(rsyncArgs).__name__ == 'str':
		#	self.rsyncArgs = rsyncArgs.split(' ')
		#else:
		#	print "rsyncArgs must be list or string...."
		#	sys.exit("Exiting.")
		
		# Save the paths to backup from the client's machine
		self.rsyncPaths = rsyncPaths

		self.rsyncArgs = [
							'-rtvvhmi8Pl',
							'--stats'
						 ]
		
		# Let's deal with the filter now...
		if useFilter:
			if customFilter == None: # If no custom filter was supplied and we need to use a filter, use the MASTER filter on the backup server
				self.filter = self.MASTER_FILTER
			else: # Otherwise, let's push the custom filter file to the backup server to use
				# The custom file will be stored on the backup server at:
				self.filter = "/tmp/filter" + str(self.ap) + ".excludes"
				# Let's *actually* send the custom filter to the backup server
				self.transferFile( customFilter, self.filter, True )
			# Let's add this option to the rsyncArgs...
			self.rsyncArgs.append( '--exclude-from=' + self.filter )

	def run( self ):
		if self.isBackup:
			self.runBackup()
		else:
			self.runRestore()

	def closeSession( self ):
		if self.cmd_channel != None:
			self.cmd_channel.close()
		if self.transport != None:
			self.transport.close()
		if self.sock != None:
			self.sock.close()

	def setLogWindow( self, logwindow ):
		self.logwindow = logwindow
		self.endMark = self.logwindow.get_buffer().create_mark("end", self.logwindow.get_buffer().get_end_iter(), False)
	
	def setProgressWindow( self, progresswindow ):
		self.progress_window = progresswindow
		self.progress_window.remote = self
	
	def log( self, text, level=logging.INFO, stream=False ):
		if level != logging.INFO:
			loglevel = getattr(logging, level.upper(), None)
			if not isinstance(loglevel, int):
				raise ValueError('Invalid log level: %s' % level)
			level = loglevel
		# Print the text to console if it is being streamed
		if stream:
			print text
		else: # otherwise, let the logger print it to console
			self.logger.log(level, text)
		if text[-1] != '\n':
			text += '\n'
		if self.logwindow != None:
			self.gobject.idle_add(self.logToGui, text)
	
	def logToGui( self, text ):
		# Append it to the end of the logwindow (at the end_iter location)
		self.logwindow.get_buffer().insert(self.logwindow.get_buffer().get_end_iter(), text)
		# Scroll the logwindow the the end
		self.logwindow.scroll_mark_onscreen(self.logwindow.get_buffer().get_insert())
	
	def error( self, msg, exit=True ):
		"""Process a warning message.
		       Preferred method: uses a 'warn' object from oitbackupgui
		       Fall-back method: print to the console
		   @param msg
		       The error/warning message to show
		   @param exit
		       Boolean determining if this should exit due to the warning
		"""
		self.log( msg, 'error' )

		self.gobject.idle_add(self.warnGui, msg)

		# If this warning should close the entire program
		if exit:
			
			#Transfer the main log to the backup server for storage
			#self.transferFile( 
			#					global_log_file, 
			#					"/client/logs/AP" + str(self.ap) + "_" + global_log_file[ global_log_file.rfind('/') + 1 : ],
			#					putOnServer=True
			#				 )
			raise Exception(msg)

	def warnGui( self, msg ):
		# If there *is* warn object provided, use it
		if self.warn != None:
			self.warn.setMsg(msg)
			self.warn.run_from_thread()
		
		#Close progress window
		if self.progress_window != None:
			self.progress_window.remote = None
			self.progress_window.cancel_clicked(None)

	def initiateSSH( self, ignoreMissingHostKey=True ):
		"""Initialize the SSH connection with a paramiko.SSHClient.
			@param ignoreMissingHostKey : (default:True)
			       Sets the missing host key policy to 'paramiko.AutoAddPolicy()
			       This allows a connection to unknown and untrusted servers
		"""
		# Create a new paramiko SSHClient object to work with
		self.ssh = paramiko.SSHClient()
		
		self.ssh.load_host_keys(self.known_hosts_file)

		if ignoreMissingHostKey:
			self.ssh.set_missing_host_key_policy( paramiko.AutoAddPolicy() )
		# /Remove #

		# Let's try *actually* opening the ssh connection with the credentials supplied
		try:
			self.ssh.connect( self.backupHost, username=self.username, password=self.password )
			self.connectionMade = True
		except paramiko.AuthenticationException, e:
			self.error("Incorrect username or password:\n" + str(e), exit=True)
		except paramiko.BadHostKeyException, e:
			self.error("The backup server's host SSH key could not be verified!\n" + str(e))
		except paramiko.SSHException, e:
			self.error("Something terrible happened while trying to open the SSH connection to the server:\n" + str(e), exit=True)
			
	def lookupHost( self ):
		"""Get the local IP address of the current machine (must be ONLINE)."""
		try:
			s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			s.connect(('www.google.com', 80))
			self.liveHost = s.getsockname()[0]
			reachedGoogle = True
			s.close()
		except Exception, e:
			reachedGoogle = False
			self.log("Could not reach www.google.com on port 80 to verify that this machine is online.")
			self.log("Trying backup server....")

		try:
			s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)	
			s.connect((self.backupHost, 22))
			self.liveHost = s.getsockname()[0]
			s.close()
		except Exception, e:
			if reachedGoogle:
				self.error("Could not reach the server on port 22 (SSH). Is the hostname correct?\n" + str(e), exit=True)
			else:
				self.error("Could not identify local IP address. Is this machine on the network?\n" + str(e), exit=True)

	def runBackup( self ):
		"""Begin rsync backup.
			This will process each path in self.rsyncPaths
			and use rsync to 'pull' the contents to the
			backup server.
		"""
		
		# First make the folder to store the backups (and logs) on the backup server
		# as rsync will not log to the as-of-yet uncreated folder
		command =  ['mkdir', '-p', self.backupPath]

		self.log("Creating remote backup path.")
		stdin, stdout, stderr = self.sshExecute( ' '.join(command), exitOnException=True )
		errors = '\n'.join(stderr.readlines())
		if errors:
			self.error("Failed to make the remote backup directory:\n" + errors, exit=True)
		# loop through the paths and rsync them one by one
		# In the future this will be replaced by using an 'includes' file and one command only
		for path in self.rsyncPaths:
			command = [ 'rsync', "-e'ssh -i "+self.ssh_key+"'" ]
			command.extend( self.rsyncArgs )
			command.extend( [ '--log-file=' + str(self.logFile) ] )
			command.extend( [ self.liveUser + '@' + self.liveHost + ':"\'' + path + '\'"', '"'+self.backupPath+'"' ] )
			self.log("Using: " + ' '.join( command ))
			#Consider using 'exitOnException=False' so that this doesn't die and exit
			#if only one rsync path fails to be backed up
			self.runCommandTransport( ' '.join( command ), self.logFile, exitOnException=True )

		#Transfer the main log to the backup server for storage
		self.log("Transferring the main log to the server.", 'debug')
		os.system( "cp -f " + global_log_file + " /tmp/temp_backup.log" )
		self.transferFile( 
							"/tmp/temp_backup.log", 
							"/logs/" + str(self.ap) + "_" + global_log_file[ global_log_file.rfind('/') + 1 : ],
							putOnServer=True
						 )
		#Cleanup
		self.closeSession()
		if self.progress_window != None:
			self.gobject.idle_add(self.progress_window.complete)
	
	def runRestore( self ):
		"""Begin rsync restore.
			This will restore everything for the particular
			appointment number to the root of the local drive.
		"""
		
		# First make sure the folder on the backup server exists for the appointment specified
		self.log( "Checking if there are backups on the remote server." )
		if not self.remotePathExists( self.backupPath ):
			self.error("No backups for " + str(self.ap) + " on backup server!", exit=True)
		
		if self.rsyncPaths[-1] != "/":
			self.rsyncPaths += "/"
		command = [ 'rsync', "-e'ssh -i "+self.ssh_key+"'" ]
		command.extend( self.rsyncArgs )
		command.extend( [ '--log-file=' + self.restoreLogFull ] )
		# self.rsyncPaths should be the path to the drive we are restoring to (in a string)
		command.extend( [ '"' + self.backupPath + '"',
						self.liveUser  + '@' + self.liveHost + ':"\'' + self.rsyncPaths + '\'"' ] )
		command.extend( [ '--exclude "' + self.restoreLog + '"'  ] )
		self.log("Using: " + ' '.join( command ))
		self.runCommandTransport( ' '.join( command ), self.restoreLogFull, exitOnException=True )
		
		# Transfer the restore log
		self.log("Copying restore log to local machine: " + self.restoreLog)
		self.transferFile( self.rsyncPaths + self.restoreLog, self.restoreLogFull, False )
		#Transfer the main log to the backup server for storage
		self.log("Transferring the main log to the backup server.", 'debug')
		os.system( "cp -f " + global_log_file + " /tmp/temp_backup.log" )
		self.transferFile( 
							"/tmp/temp_backup.log", 
							"/logs/" + str(self.ap) + "_" + global_log_file[ global_log_file.rfind('/') + 1 : ],
							putOnServer=True
						 )
		# Cleanup
		self.closeSession()
		if self.progress_window != None:
			self.gobject.idle_add(self.progress_window.complete)
		
	def remotePathExists( self, path ):
		# Try opening a secure file transfer session to the backup server
		try:
			sftp = self.ssh.open_sftp()
		# Oops....something went wrong
		except paramiko.SSHException, e:
			self.error("Caught exception while opening the SFTP connection to the backup server:\n" + str(e), exit=True)
		
		try:
			sftp.stat( path )
		except IOError, e:
			if e.errno == errno.ENOENT:
				self.log("Path does not exist on remote server: " + str(path))
				sftp.close()
				return False
			raise
		except Exception, e:
			self.error("Caught exception while checking for remote path:\n" + str(e), exit=True)
		else:
			sftp.close()
			return True
		
	
	def runCommandTransport( self, command, logFile, exitOnException=False ):
		"""Execute a command through a paramiko cmd_channel on the remote machine.
		This allows a live stream of the command's output while it is being executed.
		NOTE: This opens a new socket connection for each call!
		@type command	: string
		@param command	: The command to execute
		"""
		# Create a socket stream
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		
		# Connect to the backupHost on port 22
		self.sock.connect( (self.backupHost, 22) )
		
		# Create the transport
		self.transport = paramiko.Transport(self.sock)
		
		# Start the client
		self.transport.start_client()
		
		# Authenticate the client
		try:
			self.transport.auth_password( self.username, self.password )
		except paramiko.AuthenticationException, e:
			self.error("Incorrect username or password:\n" + str(e), exit=True)
		
		# Start a cmd channel and combine stderr and stdout for easy parsing
		try:
			self.cmd_channel = self.transport.open_session()
			self.cmd_channel.set_combine_stderr(True)
		except paramiko.SSHException, e:
			self.error("Something terrible happened while trying to open the SSH connection to the backup server:\n" + str(e), exit=True)
		
		# Run the command
		try:
			self.cmd_channel.exec_command( command )
		except paramiko.SSHException, e:
			self.error("Failed to execute command '" + command + "' on the backup server:\n" + str(e), exit=exitOnException)
		#This may only be grabbing stdout not stderr
		data = self.cmd_channel.recv(1024)
		while data:
			self.log(data, stream=True)
			if "rsync error" in data:
				self.error("Rsync error!\n"+ data +"\n**Check log on the backup server for details**\nLocated at: " + logFile)
			if self.terminate:
				stdin, stdout, stderr = self.sshExecute( 
											'pgrep -u ' + self.username + ' rsync' )
				for proc in stdout.readlines():
					print "Killing process: " + proc.strip()
					self.sshExecute( 'kill -9 ' + proc.strip() )
				self.log("Terminating transfer.")
				self.closeSession()
				self.terminate_complete = True
				break
			data = self.cmd_channel.recv(1024)
		# Try to close the socket and transports when complete
		self.closeSession()
	
	def reportProgress( self, transferredBytes, totalBytes ):
		self.log("\nTransferred: " + str(transferredBytes) + "/" + str(totalBytes) + "\n")
	
	def transferFile( self, localPath, remotePath, putOnServer=True  ):
		"""Send the custom filter file from the live host to the backup server.
			If a custom filter parameter was provided when creating a new 
			RemoteBackup object, this will push the custom filter file
			using sftp to the backup server.
		"""
		# Try opening a secure file transfer session to the backup server
		try:
			sftp = self.ssh.open_sftp()
		# Oops....something went wrong
		except paramiko.SSHException, e:
			self.error("Caught exception while opening the SFTP connection to the backup server:\n" + str(e), exit=True)

		"""
		if localPath[0] != "\"":
			localPath = "\"" + localPath
		if localPath[-1] != "\"":
			localPath += "\""
			
		if remotePath[0] != "\"":
			remotePath = "\"" + remotePath
		if remotePath[-1] != "\"":
			remotePath += "\""
		"""
		
		# We'll make 3 attempts to transfer the file (used to be: push the custom filter to the backup server)
		# (hopefully we'll only need one)
		attempts = 3
		while attempts > 0:
			if self.terminate:
				self.log("Terminating transfer.")
				self.closeSession()
				self.terminate_complete = True
				return
			# Make the transfer
			if putOnServer:
				self.log( "\nTransfering file to server: " + str(remotePath) )
				try:
					sftp.put(localPath, remotePath, callback=self.reportProgress, confirm=True )
				except IOError, e:
					if attempts > 1:
						attempts -= 1
						self.log("\nFailed to transfer to remote server, trying again....")
						pass
					else:
						self.error("Error while transfering file to remote server three times:\n" + str(e), exit=True)
				else:
					sftp.close()
					return
				"""
				# Let's make sure it exists on the backup server, as sftp.get does not raise exceptions
				stdin, stdout, stderr = self.sshExecute( "cat " + self.filterFile )
				# If there is output (file exists AND has content), AND there is nothing in the error stream, we're done
				if stdout and not stderr:
					return
				"""
			else:
				self.log( "\nTransfering file to local machine: " + str(localPath) )
				try:
					#print "using sftp.get("+remotePath+", "+localPath+")"
					sftp.get( remotePath, localPath, callback=self.reportProgress )
				except IOError, e:
					if attempts > 1:
						attempts -= 1
						self.log("\nFailed to transfer to local machine, trying again....")
						pass
					else:
						self.error("Error while getting file from remote server three times:\n" + str(e), exit=True)
				else:
					sftp.close()
					return
			# Otherwise, let's try again
		if attempts == 0:
			self.error("Error while transferring file", exit=True)
			
		# Complete, so close the sftp channel
		sftp.close()
	
	def sshExecute( self, command, exitOnException=False ):
		"""Execute a command through the paramiko.SSHClient on the remote machine.
		@type command	: string
		@param command	: The command to execute
		
		@rtype          : tuple
		@returns        : (stdin, stdout, stderr) for the
		                  command run on the remote machine
		"""
		# Try executing the given command on the backup server
		try:
			stdin, stdout, stderr = self.ssh.exec_command( command )
		except paramiko.SSHException, e:
			self.error("Failed to execute command '" + command + "' on the backup server:\n" + str(e), exit=exitOnException)
		# Command excuted successfully, now let's return the stdin, stdout, and stderr streams
		return ( stdin, stdout, stderr )
