#!/usr/bin/env python

#Import our classes
import sys, os, re, subprocess, threading, random, time, mounter, logging
from optparse import OptionParser
from re import match
from StaticGlobals import *
from hdDialog import hdDialog
from backup import backup
from restore import restore
from warning import warn

try:
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
	print "GTK/Glade not found!"
	sys.exit(1)

#Our GUI Class
class BackupGui:

	def __init__(self):
		self.logger = logging.getLogger(__name__)
		#Set the Glade file
		self.gladefile = gladeFile 
		self.wTree = gtk.glade.XML(self.gladefile, "window1") 
		self.window = self.wTree.get_widget("window1")
		self.logger.debug("Initialized.")
			
		#Create our dictionary and connect it
		dic = { "on_select_drive_backup_button_clicked" : self.select_drive_backup_button_clicked,
				"on_select_drive_restore_button_clicked" : self.select_drive_restore_button_clicked,
				"on_backup_button_clicked" : self.backup_button_clicked,
				"on_external_restore_button_clicked": self.external_restore_button_clicked,
				"on_filter_box_toggled": self.filter_box_toggled,
				"on_local_box_backup_toggled": self.local_box_backup_toggled,
				"on_local_box_restore_toggled": self.local_box_restore_toggled,
				"on_restore_button_clicked" : self.restore_button_clicked,
				"on_external_backup_button_clicked" : self.external_backup_button_clicked,
				"on_window1_destroy" : self.notifyAndQuit }
		self.logger.debug("Connectiong gui dictionary.")
		self.wTree.signal_autoconnect(dic)
		
		#Set all of the widgets we may change
		self.combo = self.wTree.get_widget("combo1")
		self.combo2 = self.wTree.get_widget("combo2")
		self.label = self.wTree.get_widget("label11")
		self.label24 = self.wTree.get_widget("label24")
		self.label4 = self.wTree.get_widget("label37")
		self.select_drive_restore_button = self.wTree.get_widget("select_drive_restore_button")
		self.external_backup_button = self.wTree.get_widget("external_backup_button")
		self.textview2 = self.wTree.get_widget("textview2")
		self.table1 = self.wTree.get_widget("table1")
		self.table2 = self.wTree.get_widget("table2")
		self.table3 = self.wTree.get_widget("table3")
		self.table4 = self.wTree.get_widget("table4")
		self.table5 = self.wTree.get_widget("table5")
		self.table6 = self.wTree.get_widget("table6")
		self.label39 = self.wTree.get_widget("label39")
		self.label11 = self.wTree.get_widget("label11")
		self.notebook = self.wTree.get_widget("notebook1")
		
		#Set Boolean Variables
		self.BUTTON_SWITCH = False
		self.FILTER = True
		self.LOCAL = False
		self.FOLDERS = False
		
		#Set Default Server
		self.SERVER = REMOTE_BACKUP_SERVER
		self.wTree.get_widget("server_field_backup").set_text(self.SERVER)
		
		#Set out Hard Drives as blank Strings (initiate) 
		self.hd_name = ""
		self.external_name = ""
		self.folders_selected = []
		self.hd_name_backup= ""
		self.external_name_backup= ""
		self.folders_selected_backup = []
		
		#Build our log window
		self.logwindow = gtk.TextBuffer(None)
		
		#Hide any unwanted widgets once the window loads
		if self.LOCAL == False:
			self.select_drive_restore_button.hide()
			self.external_backup_button.hide()
		
		self.logger.debug("Gui fully initialized.")
	
	def notifyAndQuit(self, widget):
		self.logWarning(
			"**********\nLog will be located at: %s \n**********\nPLEASE SAVE THE LOG\n**********" % global_log_file,
			title="Please Note")
		gtk.main_quit()
	
	#Check generic input
	def check_input(self, to_test, pattern, invalid_msg, input_type):
		to_return = to_test
		if to_test == '' or None:
			msg = "You entered a blank " + input_type + "."
			self.logWarning(msg)
		else:
			if re.match( pattern, to_test) is None:
				self.logWarning(invalid_msg)
			else:
				return to_return

	def logWarning(self, msg, title=None):
		self.logger.warn(msg)
		warning = warn(msg)
		warning.setTitle(title)
		warning.run()
	
	#Create a function for when the HD button is pressed (BACKUP)
	def select_drive_backup_button_clicked(self, widget):
		#Button_switch determines if the 'Individual Folders' button should be displayed
		self.BUTTON_SWITCH = False
		#Run a new HD selector
		hdView = hdDialog(self.BUTTON_SWITCH,self.FOLDERS);
		input,name,self.FOLDERS,self.folders_selected_backup = hdView.run()
		
		#Check if user pressed Ok and assign HD name
		if (input == gtk.RESPONSE_OK) :
			if self.FOLDERS == False:
				if(name!=""):
					#Assign the hard drive name
					self.hd_name_backup=name
					#Tell the user what HD we will backup
					self.label11.set_text("Backing up "+ self.hd_name_backup)
					
					#Also set it in the output tab
					self.logwindow.set_text("Backing up " + self.hd_name_backup)
					self.textview2.set_buffer(self.logwindow)
					
					#If it's a local backup, also set what we're backing up to
					if self.LOCAL == True:
						self.label11.set_text("Backing up " + self.hd_name_backup + " to " + self.external_name_backup)
			else:
				for folder in self.folders_selected_backup:
					#Make sure there are actual folders
					if(folder!="" or None):
						#Set the label for what we're backing up
						self.label11.set_text("Backing up selected folder(s)")
						
						#Setup the textbuffer
						current_folders = str(self.folders_selected_backup)
						#Put a line break between each folder
						foo = current_folders.replace(",",'\n')
						#Set the output textview
						self.logwindow.set_text("Backing up: " + foo)
						self.textview2.set_buffer(self.logwindow)
						
						#If it's a local backup
						if self.LOCAL == True:
							self.label11.set_text("Backing up selected folder(s) to " + self.external_name_backup)

	#Function for when HD button is pressed (RESTORE)
	def select_drive_restore_button_clicked(self, widget):
		#Displays individual folders
		self.BUTTON_SWITCH = False
		#Create a new HD view
		hdView = hdDialog(self.BUTTON_SWITCH,self.FOLDERS);
		input,name,self.FOLDERS,self.folders_selected = hdView.run()
		
		#Check if user pressed Ok and assign HD name
		if (input == gtk.RESPONSE_OK) :
			if self.FOLDERS == False:
				if(name!=""):
					#Assign the hard drive name
					self.hd_name=name
					#Tell the user what HD we will restore
					self.label39.set_text("Restoring from "+ self.external_name)
					
					self.logwindow.set_text("Restoring from " + self.external_name)
					self.textview2.set_buffer(self.logwindow)
					
					if self.LOCAL == True:
						self.label39.set_text("Restoring from " + self.hd_name + " to " + self.external_name)
			else:
				for folder in self.folders_selected:
					#Make sure there are actual folders
					if(folder!="" or None):
						self.label39.set_text("Restoring from selected folder(s)" + " to " + self.external_name)
					#Setup the textbuffer
						current_folders = str(self.folders_selected)
						#Put a line break between each folder
						foo = current_folders.replace(",",'\n')
						#Set the output textview
						self.logwindow.set_text("Restoring from: " + foo)
						self.textview2.set_buffer(self.logwindow)


	#Create a function for when the backup button is pressed (BACKUP)
	def backup_button_clicked(self, widget):
		global num_files
		#Build our widgets
		self.server = self.wTree.get_widget("server_field_backup")
		self.name = self.wTree.get_widget("username_field_backup")
		self.pswrd = self.wTree.get_widget("password_field_backup")
		self.ap = self.wTree.get_widget("ap_field_backup")
		#Get our field text
		self.SERVER = self.server.get_text()
		un = self.name.get_text()
		ps = self.pswrd.get_text()
		an = self.ap.get_text()

		#If user selected a local rsync, check they selected an external device
		if self.LOCAL == True:
			appointment_number = an
			username = un
			#Check the external drive
			external_drive_backup = self.check_input(self.external_name_backup,'.','Invalid External HD!','External Device')
			if self.FOLDERS == True:
				for folder in self.folders_selected_backup:
					#Check all folders selected
					current_folder = self.check_input(folder,'.','Invalid Folders','Folder(s)')
			else:
				#Otherwise check the hard drive
				hard_drive_backup = self.check_input(self.hd_name_backup,'.','Invalid HD!','Hard Drive')
				
			
			#Ensure an external drive is selected
			if (external_drive_backup != None):

				#Make sure a folder has been selected
				if (self.FOLDERS == True and current_folder == None):
					return
				#Or that a hard drive has been selected
				if (self.FOLDERS == False and hard_drive_backup == None):
					return
				else:
					#Set appropriate names
					appointment_number = "HR" + appointment_number
					external_drive_backup = '/media/' + external_drive_backup + '/'
					if self.FOLDERS:
						#Change the gui tab to output
						self.notebook.set_current_page(2)
						
						#Create new appointment
						appointment = backup(
												appointment_number=appointment_number,
												paths_to_backup=self.folders_selected_backup,
												username=username,
												use_filter=self.FILTER,
												remote_path_arg=external_drive_backup,
												gui_enabled=True
											)
											
						self.grab_set_coords(appointment)
						appointment.set_log_window(self.textview2)
						appointment.run()
																			
						#After backup is complete, reset selected drives
						external_drive_backup = ""
						#Clear labels and Output
						self.label11.set_text("")
						self.logwindow.set_text("")
						self.textview2.set_buffer(self.logwindow)
					else:
						hard_drive_backup = '/media/' + hard_drive_backup + '/'
						#Change the gui tab to output
						self.notebook.set_current_page(2)
						
						#Create a new appointment
						appointment = backup(
												appointment_number=appointment_number,
												paths_to_backup=hard_drive_backup,
												username=username,
												use_filter=self.FILTER,
												remote_path_arg=external_drive_backup,
												gui_enabled=True
											)
						self.grab_set_coords(appointment)
						appointment.set_log_window(self.textview2)
						appointment.run()
																			
						#After backup is complete, reset selected drives
						self.hd_name_backup = self.external_name_backup = ""
						#Clear labels and output
						self.label11.set_text("")
						self.logwindow.set_text("")
						self.textview2.set_buffer(self.logwindow)
				
		#If the rsync is to the server
		else:
			#Check all credentials to make sure they're valid inputs
			username = self.check_input(un,'^[a-zA-Z0-9]{1,40}$', 'Username must be 1-40 characters and lower/upper case letters, or numbers.', 
			'username')
			appointment_number = self.check_input(an, '^\d{6}$', 'Invalid appointment number.','appointment number')
			password = self.check_input(ps,'.','Invalid password!!','password')
			
			if self.FOLDERS == True:
				#Check folders
				for folder in self.folders_selected_backup:
					current_folder = self.check_input(folder,'.','Invalid Folders','Folder(s)')
			else:
				#Otherwise check hard drive
				hard_drive_backup = self.check_input(self.hd_name_backup,'.','Invalid HD! Impossible, see Jake!','Hard Drive')
		
			#Check that all inputs are valid then backup
			if (username and appointment_number and password)!=None:
				if (self.FOLDERS == True and current_folder == None):
					return
				if (self.FOLDERS == False and hard_drive_backup == None):
					return
				else:
					#Set appropriate names
					appointment_number = "HR" + appointment_number
					
					if self.FOLDERS:
						#Change the gui tab to output
						self.notebook.set_current_page(2)
						
						appointment = backup(
												appointment_number=appointment_number,
												username=username,
												password=password,
												paths_to_backup=self.folders_selected_backup,
												use_filter=self.FILTER,
												backup_server=self.SERVER,
												gui_enabled=True
											)
						self.grab_set_coords(appointment)
						appointment.set_log_window(self.textview2)
						appointment.run()
												
						#Clears label and output
						self.label11.set_text("")
						self.logwindow.set_text("")
						self.textview2.set_buffer(self.logwindow)
						self.FOLDERS = None
					else:
						hard_drive_backup = '/media/' + hard_drive_backup + '/'
						#Change the gui tab to output
						self.notebook.set_current_page(2)
						
						appointment = backup(
												appointment_number=appointment_number,
												username=username,
												password=password,
												paths_to_backup=hard_drive_backup,
												use_filter=self.FILTER,
												backup_server=self.SERVER,
												gui_enabled=True
											)
						self.grab_set_coords(appointment)
						appointment.set_log_window(self.textview2)
						appointment.run()
												
						#After backup is complete, reset selected drives
						self.hd_name_backup = ""
						#Clears label and output
						self.label11.set_text("")
						self.logwindow.set_text("")
						self.textview2.set_buffer(self.logwindow)
						

	#Create a function for when the restore button is pressed (RESTORE)
	def restore_button_clicked(self,widget):
		self.logger.debug(str(self.folders_selected))
		self.server = self.wTree.get_widget("server_field_restore")
		self.name = self.wTree.get_widget("username_field_restore")
		self.pswrd = self.wTree.get_widget("password_field_restore")
		self.ap = self.wTree.get_widget("ap_field_restore")
		#Get our field text
		self.SERVER = self.server.get_text()
		un = self.name.get_text()
		ps = self.pswrd.get_text()
		an = self.ap.get_text()
		
		#If user selected a local rsync, check they selected an external device
		if self.LOCAL == True:
			appointment_number = an
			username = un
			#Check the external drive
			external_drive = self.check_input(self.external_name,'.','Invalid External HD!','External Device')
			
			if self.FOLDERS == True:
				for folder in self.folders_selected:
					#Check all folders selected
					current_folder = self.check_input(folder,'.','Invalid Folders','Folder(s)')
			else:
				#Otherwise check the hard drive
				hard_drive = self.check_input(self.hd_name,'.','Invalid HD! Impossible, see Jake!','Hard Drive')
				
			
			#Ensure an external drive is selected
			if (external_drive != None):

				#Make sure a folder has been selected
				if (self.FOLDERS == True and current_folder == None):
					return
				#Or that a hard drive has been selected
				if (self.FOLDERS == False and hard_drive == None):
					return
				else:
					#Set appropriate names
					appointment_number = "HR" + appointment_number
					external_drive = '/media/' + external_drive + '/'
					if self.FOLDERS:
						#Change the gui tab to output
						self.notebook.set_current_page(2)
						
						#Create new appointment
						restoration = restore(
												appointment_number=appointment_number,
												username=username,
												path_to_restore_to=external_drive,
												remote_path_arg = self.folders_selected,
												gui_enabled=True
											)
						self.grab_set_coords(restoration)
						restoration.set_log_window(self.textview2)
						restoration.run()
						
						#After restore is complete, reset selected drives
						external_drive = ""
						self.label39.set_text("")
						self.logwindow.set_text("")
						self.textview2.set_buffer(self.logwindow)
					else:
						hard_drive = '/media/' + hard_drive + '/'
						#Change the gui tab to output
						self.notebook.set_current_page(2)
						
						#Create a new appointment
						restoration = restore(
												appointment_number=appointment_number,
												username=username,
												path_to_restore_to=external_drive,
												remote_path_arg = hard_drive,
												gui_enabled=True
											)
						self.grab_set_coords(restoration)
						restoration.set_log_window(self.textview2)
						restoration.run()
												
						#After restore is complete, reset selected drives
						self.hd_name = self.external_name = ""
						self.label39.set_text("")
						self.logwindow.set_text("")
						self.textview2.set_buffer(self.logwindow)
				
		#If the rsync is to the server
		else:
			#Check all credentials to make sure they're valid inputs
			username = self.check_input(un,'^[a-zA-Z0-9]{1,40}$', 'Username must be 1-40 characters and lower/upper case letters, or numbers.', 
			'username')
			appointment_number = self.check_input(an, '^\d{6}$', 'Invalid appointment number.','appointment number')
			password = self.check_input(ps,'.','Invalid password!!','password')
			
			self.logger.info("Checking HD: " + self.external_name)
			#Check hard drive
			external_drive = self.check_input(self.external_name,'.','Invalid HD!','Hard Drive')
			self.logger.info("Checked HD.")
		
			#Check that all inputs are valid then restore
			if (username and appointment_number and password)!=None:
				if (external_drive == None):
					return
				else:
					#Set appropriate names
					appointment_number = "HR" + appointment_number
					
					external_drive = '/media/' + external_drive + '/'
					#Change the gui tab to output
					self.notebook.set_current_page(2)
					
					restoration = restore(
											appointment_number=appointment_number,
											username=username,
											password=password,
											path_to_restore_to=external_drive,
											backup_server=self.SERVER,
											gui_enabled=True
										)
					self.grab_set_coords(restoration)
					restoration.set_log_window(self.textview2)
					restoration.run()
											
					#After restore is complete, reset selected drives
					self.external_name = ""
					self.label39.set_text("")
					self.logwindow.set_text("")
					self.textview2.set_buffer(self.logwindow)

	#External HD function (RESTORE)
	def external_restore_button_clicked(self,widget):
		#Turn off Button_switch so no 'Individual Folder' button is shown
		self.BUTTON_SWITCH = True
		hdExternal = hdDialog(self.BUTTON_SWITCH,self.FOLDERS);
		input, name, self.FOLDERS= hdExternal.run()
		
		if (input == gtk.RESPONSE_OK):
			if(name!=""):
				self.external_name = name
				if self.FOLDERS:
					self.label39.set_text("Restoring from selected folder(s) to " + self.external_name )
				else:
					self.label39.set_text("Restoring from " + self.hd_name + " to " + self.external_name)
				
	#External HD function (BACKUP)
	def external_backup_button_clicked(self,widget):
		#A switch to display the individual folders button
		self.BUTTON_SWITCH = True
		hdExternal = hdDialog(self.BUTTON_SWITCH,self.FOLDERS);
		input, name, self.FOLDERS = hdExternal.run()
		
		if (input == gtk.RESPONSE_OK):
			if(name!=""):
				self.external_name_backup = name
				if self.FOLDERS:
					self.label11.set_text("Backing up selected folder(s) to " + self.external_name_backup)
				else:
					self.label11.set_text("Backing up " + self.hd_name_backup + " to " + self.external_name_backup)

	#Function for when the filter box is checked (BACKUP)
	def filter_box_toggled(self,widget):
		#If it is checked, turn on the filter switch
		if widget.get_active() == True:
			self.FILTER = True
		else:
			self.FILTER = False
	
	#Function for when the local box is checked (BACKUP)
	def local_box_backup_toggled(self,widget):
		
		#If it is checked, turn on local, reset external name, and hide/show various  widgets
		if widget.get_active() == True:
			self.LOCAL = True
			self.external_name_backup = ""
			self.combo2.hide()
			self.external_backup_button.show()
			self.label4.set_text('Please select the device to backup to')
			self.table2.hide()
			self.table3.hide()
			self.logger.debug(str(self.LOCAL))
			
		#If it is checked off, turn off local, reset external name, and hide/show various  widgets
		else:
			self.LOCAL = False
			self.label.set_text("")
			self.external_name_backup = ""
			self.combo2.show()
			self.external_backup_button.hide()
			self.label4.set_text('Please select the Server')
			self.table2.show()
			self.table3.show()

	#Function for when the local box is checked (RESTORE)
	def local_box_restore_toggled(self,widget):
		
		#If it is checked, turn on local, reset external name, and hide/show various  widgets
		if widget.get_active() == True:
			self.LOCAL = True
			self.external_name = ""
			self.combo.hide()
			self.select_drive_restore_button.show()
			self.label24.set_text('Please select the device to restore from')
			self.table4.hide()
			self.table5.hide()
			
		#If it is checked off, turn off local, reset external name, and hide/show various  widgets
		else:
			self.LOCAL = False
			self.label39.set_text("")
			self.external_name = ""
			self.combo.show()
			self.select_drive_restore_button.hide()
			#self.label24.set_text('Please select the Server')
			self.table4.show()
			self.table5.show()
			
	def grab_set_coords(self,appointment):
		#Get our window coordinates (North East corner)
		self.window.set_gravity(gtk.gdk.GRAVITY_NORTH_EAST)
		width,height = self.window.get_size()
		coordsx,coordsy = self.window.get_position()
		coordsx += width
		appointment.set_window_coordinates(coordsx,coordsy)
 
