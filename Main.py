#!/usr/bin/env python

import os, sys, mounter, logging, lock
from optparse import OptionParser
from StaticGlobals import global_log_file, default_log_level

#Checks if the user running the script is root
def isRoot():
	# root uid=0, so anything else is NOT root
	if os.getuid():
		print "You must be root to run this script."
		print "Use 'su' to become root first, then try again, or run with 'sudo'."
		return False
	return True


def initializeParser():
	parser = OptionParser(
		usage = "usage: %prog [options]",
		description = "Remote Server Backup GUI")
	
	parser.add_option(	"-a",
						"--all",
						action = "store_false",
						dest = "use_filter",
						help = "Runs the script withOUT a filter (runs on ALL files and folders specified).")
	
	parser.add_option(	"-e",
						"--external-path",
						dest = "external_path",
						help = "Specifies a location other than the backup server for the backups to be stored/restored from.")
	
	parser.add_option(	"--filter",
						action = "store_true",
						dest = "use_filter",
						default = True,
						help = "Runs the script with a filter (default).")
	
	parser.add_option(	"-g",
						"--gui",
						action = "store_true",
						dest = "useGUI",
						default = False,
						help = "Run with a graphical user interface (GUI).")
	
	parser.add_option(	"-l",
						"--log",
						dest = "loglevel",
						help = "The threshold for logging purposes. Use \"DEBUG\" for high verbosity.")
	
	parser.add_option(	"-m",
						"--mount",
						action = "store_true",
						dest = "mount",
						default = False,
						help = "Runs 'mounter' to help mount/unmount partitions before backing up/restoring. r00t priviliges required!!!")
	
	parser.add_option(	"-n",
						"--appointment-number",
						dest = "appointment_number",
						help = "An Appointment Number (e.g. 001234)")
	
	parser.add_option(	"-r",
						"--restore",
						action = "store_true",
						dest = "restore",
						default = False,
						help = "Restore backups (use \"-e\" to specify an external location to restore from.)")
						
	parser.add_option(	"-s",
						"--server",
						dest = "server",
						help = "Specifies a server for the backup/restore.")
	
	"""	
	parser.add_option("-t",
					"--test",
					action="store_true",
					dest = "testMode",
					default = False,
					help = "Run in test mode, for use while developing.")
	"""
	
	parser.add_option(	"-u",
						"--username",
						dest = "username",
						help = "Server Username.")
	
	return parser

def checkArgs(options, args):
	"""Given a list of options from the arguments (through an Optionparser),
	check them and act approriately
	"""
	# Handle varying log levels
	setupLogging(options.loglevel)
	
	# Create a lock object
	lk = lock.lock()
	# and acquire the lock
	lk.acquire()
	
	# Automount stuff
	mounter.autoMount()
	
	#If we're running the GUI
	if options.useGUI:
		logging.debug("Attempting to setup GUI.")
		try: #importing the gtk libraries
			import pygtk
			pygtk.require("2.0")
			import gobject
		except:
			pass
		try:
			import gtk
			import gtk.glade
			import gobject
		except:
			logging.error("Unable to start the GUI!")
			sys.exit("Cannot start GUI because Gtk is not available! Please make sure you are running in a graphical environment and that Gtk is installed.")
		# Now add a console logging handler
		addConsoleHandler()
		#Now that the libraries are imported, start the GUI
		logging.debug("Importing BackupGui for gui.")
		from backupgui import BackupGui
		hwg = BackupGui()
		logging.debug("Initializing gobject threading.")
		gobject.threads_init()
		logging.debug("Starting gtk.main().")
		gtk.main()
	#Otherwise, we're running the command line interface (CLI)
	else:
		#Import important methods for the CLI
		logging.debug("Importing BackupCLI for command-line environment.")
		from backupcli import BackupCLI
		logging.debug("Parsing input for CLI.")
		hwg = BackupCLI(options, args)
		logging.debug("Starting cli.")
		hwg.start()
		print "\n\n**********\nLog will be located at: %s \n**********\n\n" % global_log_file
		print "**********\nPLEASE SAVE THE LOG\n**********\n\n"
	
	# Release the lock file
	lk.release()
	
def setupLogging(lvl):
	loglevel = getattr(logging, default_log_level.upper(), None)
	if not isinstance(loglevel, int):
		raise ValueError('Invalid DEFAULT log level: %s' % default_log_level)
	if lvl:
		loglevel = getattr(logging, lvl.upper(), None)
		if not isinstance(loglevel, int):
			raise ValueError('Invalid log level: %s' % lvl)
	logging.basicConfig(
						format='%(asctime)s %(name)-18s: %(levelname)-8s %(message)s',
						datefmt='%m/%d/%Y %I:%M:%S %p',
						filename=global_log_file,
						filemode='a', # This will append to any previous log that exists, instead of overwriting
						level=loglevel
						)
	logging.info("\n\n\n\n\n\n\n\n\n\n")
	logging.info("Logging initialized.")
	

def addConsoleHandler():
	# define a Handler which writes INFO messages or higher to the sys.stderr
	console = logging.StreamHandler()
	console.setLevel(logging.INFO)
	# set a format which is simpler for console use
	formatter = logging.Formatter('%(name)-18s: %(levelname)-8s %(message)s')
	# tell the handler to use this format
	console.setFormatter(formatter)
	# add the handler to the root logger
	logging.getLogger('').addHandler(console)
	logging.info("Console handler for logging initialized.")

def start():
	"""Create an OptionParser, and try to interpret the command line arguments"""
	parser = initializeParser()
	(options, args) = parser.parse_args()
	checkArgs(options, args)

if __name__ == "__main__":
	print
	if not isRoot():
		sys.exit("\nExiting: need r00t priviliges!\n")
	start()
