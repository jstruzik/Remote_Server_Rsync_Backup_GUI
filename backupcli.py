import os, re, sys, readline, glob, logging
from backup import backup
from restore import restore
from getpass import getpass
from StaticGlobals import *

class BackupCLI():

	def __init__(self, options, args):
		self.logger = logging.getLogger(__name__)
		self.options = options
		self.args = args
		self.SERVER = REMOTE_BACKUP_SERVER
		self.logger.debug("Initialized.")
		
	
	#Asks for the user's confirmation
	def confirm_yes_no(self, question):
		#We'll want to keep track of how many time the consultant tries and fails.
		tries = 0
		
		#Keep asking for a response.
		while True:
			#We'll want to stop after 5 tries. 
			if tries == 5:
				sys.exit( "You're not reading directions or something is terribly wrong. Later.")
			sys.stdout.write (question + " [yes/no]:")
			answer = sys.stdin.readline().strip()
			
			#We'll ask again if there was no answer.
			if not answer:
				os.system("clear")
				print( "Please enter a response!")
				continue
			try:
				if not re.match( 'yes|no', answer, re.I ):
					os.system("clear")
					print "Invalid response. Try again."
					tries += 1
					continue
				if re.match( 'yes', answer, re.I ):
					return True
				elif re.match( 'no', answer, re.I ):
					return False
				else:
					continue
			except(TypeError):
				self.error("Something terrible happened that should have been caught already?")
				sys.exit("Bad response that should have been caught already. Tell Wes that something has gone terribly terribly wrong.")
		
	#Validate generic input
	#See check_input for argument details
	def valid_input(self, to_test, tries, pattern, invalid_msg, input_type, quiet=False):
		try:
			if re.match( pattern, to_test) is None:
				if not quiet:
					print (invalid_msg)
				return False
			else:
				return True
		except(TypeError):
			if to_test is None:
				if tries > 0:
					print("You entered a blank " + input_type + ".")
			else:
				to_test_pr = []
				to_test_pr.append(to_test)
				print( to_test_pr + " is an invalid " + input_type + ".")

	#Check generic input
	# to_test = string to check
	# pattern = regex to check against
	# invalid_msg = message to display on invalid input
	# input_type = type of input being checked (e.g. appt number, username, etc)
	# success_msg = message to display on valid input
	# prompt = message to prompt user with
	# confirm = boolean flag to use confirm_yes_no()
	def check_input(self, to_test, pattern, invalid_msg, input_type, success_msg, prompt, confirm):
		tries = 0
		to_return = to_test
		if self.valid_input(to_return, tries, pattern, invalid_msg, input_type, True):
			return to_return
		else:
			while not self.valid_input(to_return, tries, pattern, invalid_msg, input_type):
				#If the consultant has tried more than five times, something is wrong.
				if tries == 5:
					sys.exit( "You have tried to enter the " + input_type + " unsuccessfully six times. Exiting.")
				if tries > 0:
					print ( "\"" + to_return + "\" is an invalid " + input_type + ".")
				tries += 1
				print
				sys.stdout.write( prompt )
				to_return = sys.stdin.readline().strip()
		
		print (success_msg + to_return)
		
		if confirm:
			os.system("clear")
			if not self.confirm_yes_no( "Is " + to_return + " correct?" ):
				self.logger.error("User aborted mission.")
				sys.exit( "You have elected to abort this mission!" )
		return to_return

	#Check the paths to backup/restore
	def check_paths(self, to_test):
		tries = 0
		if type( to_test ).__name__ == 'str':
			to_return = to_test.split(';')
		else:
			to_return = to_test
		if self.valid_paths(to_return, tries):
			print "Using:"
			final_to_return = []
			for path in to_return:
				print path
				#Let's put each path in its own double quotes to take care of weird characters"
				final_to_return.append('"' + path + '"')
			return final_to_return
		else:
			readline.set_completer_delims(' \t\n;')
			readline.parse_and_bind("tab: complete")
			readline.set_completer(self.complete)
			while len(to_return) == 0 or not self.valid_paths(to_return, tries):
				if tries == 5:
					self.logger.error("User entered the paths unsuccessfully 6 times.")
					sys.exit( "You have tried to enter the paths unsuccessfully six times. Exiting." )
				if tries > 0:
					os.system('clear')
					print "\"" + ';'.join(to_return) + "\" is an invalid list of paths."
					print
				tries += 1
				print "Please enter all paths, separated with ONLY a semicolon (---no spaces---)."
				print "Example input (with or without trailing slashes):"
				print "  /media/backup_volume/;/media/disk1/file.txt;/media/path/to/folder/or/file"
				print
				print "Use the [TAB] button to help auto-complete the paths (press twice to get a list)"
				to_return = raw_input("Paths: ")
				print "Checking paths: " + to_return
				to_return = to_return.strip("\n")
				to_return = to_return.split(';')

		os.system('clear')
		print
		print "Congratulations, you have selected available paths!"
		print
		print "Using:"
		final_to_return = []
		for path in to_return:
			print path
			#Let's put each path in its own double quotes to take care of weird characters"
			final_to_return.append('"' + path + '"')
		return final_to_return

	def complete(self, text, state):
		return (glob.glob(text+'*')+[None])[state]
	
	def valid_paths(self, paths, tries):
		try:
			if len(paths) == 0:
				return False
			for path in paths:
				if os.path.exists(path) and ( os.path.isdir(path) or os.path.isfile(path) ):
					continue
				else:
					return False
			return True
		except TypeError:
			if paths is None:
				if tries > 0:
					print "You entered a blank path."
			else:
				paths_pr = []
				paths_pr.append(paths)
				print paths_pr + " is an invalid input for paths."
			print
			return False

	def start(self):
		#Check the username from input
		username = self.options.username
		self.logger.debug("Checking username input.")
		if username == '' or username == None:
			print "You must enter a username!"

		username = self.check_input( username, 
								'^[a-zA-Z0-9]{1,40}$', 
								'Username must be 1-40 characters and lower/upper case letters, or numbers.', 
								'username', 
								'Using the following as your username: ', 
								'Please enter your username (i.e. for the Mac Workstations):',
								False)
		
		#Check the appointment number from input
		appointment_number = self.options.appointment_number
		self.logger.debug("Checking appointment number input.")
		if appointment_number == '' or appointment_number == None:
			print "You must enter an appointment number!"
		
		appointment_number = 'HR' + self.check_input(	appointment_number,
													'^\d{6}$',
													'Invalid appointment number.',
													'appointment number',
													'The appointment will be labeled as: HR',
													'Please enter the help request number (e.g. 001234): HR',
													True)
		
		#Let the user mount/unmount partitions if necessary
		if self.options.mount:
			self.logger.debug("Trying to load 'mounter' for manual mounting.")
			try:
				import mounter
				print "Please select the partition to be mounted and backed up."
				m = mounter()
				m.start()
			except:
				print "Could not load 'mounter' - skipping."
		
		#Checking paths to backup from input
		self.logger.debug("Checking backup paths from input.")
		if not self.options.restore:
			self.logger.debug("This is a BACKUP.")
			paths_to_backup = self.check_paths(self.args)
		else:
			self.logger.debug("This is a RESTORE.")
			path_to_restore_to = self.check_paths(self.args)
		
		#Change in server
		if self.options.server != '' and self.options.server != None:
			self.logger.debug("Changing server setting.")
			self.SERVER = self.options.server
			print "New Server:" + self.SERVER
		
		#Check remote path
		remote_path_available = False
		external_path = self.options.external_path
		self.logger.debug("Checking remote path.")
		if external_path != '' and external_path != None:
			external_path = ''.join(self.check_paths(external_path))
			remote_path_available = True
		
		#Now we'll create an appointment object. We'll use it as the object through which we perform backups.
		self.logger.debug("Creating appointment object (backup or restore) to perform backups/restores.")
		if not self.options.restore:
			self.logger.debug("Using a backup object....")
			if remote_path_available:
				self.logger.debug("Creating local backup object.")
				appointment = backup(
										appointment_number=appointment_number,
										username=username,
										paths_to_backup=paths_to_backup,
										use_filter=self.options.use_filter,
										remote_path_arg=external_path
									)
			else:
				self.logger.debug("Creating remote backup object (after getting password).")
				#We need a password
				password = getpass()
				appointment = backup(
										appointment_number=appointment_number,
										username=username,
										password=password,
										paths_to_backup=paths_to_backup,
										backup_server=self.SERVER,
										use_filter=self.options.use_filter
									)
			#Start the backup
			self.logger.debug("Starting the backup job.")
			appointment.run()
		else:
			self.logger.debug("Using a restore object.....")
			if type(path_to_restore_to).__name__ == "list":
				self.logging.info("Multiple paths to restore to, so using the first one.")
				path_to_restore_to = path_to_restore_to[0]
				print
				print "Using first argument ("+path_to_restore_to+") as the path to restore to."
				print
			if remote_path_available:
				self.logger.debug("Creating local restore object.")
				#do restore from remote path
				restoration = restore(
										appointment_number=appointment_number,
										username=username,
										path_to_restore_to=path_to_restore_to,
										remote_path_arg=external_path
									)
			else:
				self.logger.debug("Creating remote restore object.")
				#do default restore from backup server
				#We need a password
				password = getpass()			
				restoration = restore(
										appointment_number=appointment_number,
										username=username,
										password=password,
										path_to_restore_to=path_to_restore_to,
										backup_server=self.SERVER
									)
			#Start the restore
			self.logger.debug("Starting the restore job.")
			restoration.run()
