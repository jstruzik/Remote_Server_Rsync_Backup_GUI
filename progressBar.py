import sys, os, subprocess,re, logging
from time import sleep
from StaticGlobals import gladeFile

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

#Creates a new progress bar window		
class progress:
	def __init__(self,coordsx,coordsy,gf=gladeFile):
		self.logger = logging.getLogger(__name__)
		#Set our progress variables
		self.gladefile = gf
		self.PULSE = False
		self.local = False
		self.remote = None
		self.coordsx = coordsx
		self.coordsy = coordsy
		self.logger.debug("Initialized.")
			
	def run(self):
		#Build our progress window and bar
		self.wTree = gtk.glade.XML(self.gladefile, "process_window")
		self.pw = self.wTree.get_widget("process_window")
		self.pbar = self.wTree.get_widget("progressbar")
		self.cancel = self.wTree.get_widget("cancel_button")
		self.pbar.set_fraction(0.0)
		self.pbar.set_text("Processing...Please Wait")
		
		#Move the progress window to the right of the GUI
		self.pw.move(self.coordsx,self.coordsy)
		
		#Create the dictionary
		dic = { "on_cancel_button_clicked" : self.cancel_clicked}
		self.wTree.signal_autoconnect(dic)
		
		#If we want to pulse, call update
		if self.PULSE == True:
			gtk.timeout_add(100, self.update)
	
	#Sets the text of the progress bar
	def set_text(self, text):
		self.pbar.set_text(text)
	
	def cancel_clicked(self, widget):
		#Destroy threads
		if self.pbar.get_text() != "Complete!":
			#Kills remote backup threads
			if self.remote != None:
				self.remote.terminate = True
				while not self.remote.terminate_complete:
					sleep(1)
				if self.current_thread.isAlive():
					self.logger.debug("Thread is still alive!")
					try:
						self.logger.debug("Stopping thread....")
						self.current_thread._Thread__stop()
						self.logger.info("Thread stopped.")
					except:
						self.logger.error("Could not be killed!")
		
		
			#Kills local backup threads			
			if self.local == True:
				if self.current_thread.isAlive():
					self.logger.debug("Thread is still alive!")
					try:
						self.logger.debug("Stopping thread....")
						self.current_thread._Thread__stop()
						self.logger.info("Thread stopped.")
					except:
						self.logger.error("Could not be killed!")
				self.local = False
		#Destroy the progress window (do this LAST or else we can't check the text above)
		self.pw.destroy()
	
	#Updates the progress bar so it pulses properly	
	def update(self):
		if self.PULSE == True:
			self.pbar.pulse()
		while gtk.events_pending():
			gtk.main_iteration()
		return True
	
	#Used to set the progress bar fraction of completion	
	def set_fraction(self, percent):
		self.pbar.set_fraction(percent)
		while gtk.events_pending():
			gtk.main_iteration()
	
	def set_current_thread(self,thread):
		self.current_thread = thread
	
	#Destroys the progress window
	def destroy(self):
		self.pw.destroy()
	
	#Sets the progress bar to completed	
	def complete(self):
		self.PULSE = False
		self.pbar.set_fraction(1.0)
		self.pbar.set_text("Complete!")
		self.cancel.set_label("Okay")
