#!/usr/bin/env python

import sys, os, subprocess,re, logging
from time import sleep

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

gladeFile = "backupgui.glade"

#Create a warning dialog
class warn():
	#Builds the warning dialog for checks
	def __init__(self, WARNING_MESSAGE):
		self.logger = logging.getLogger(__name__)
		self.WARNING_MESSAGE = WARNING_MESSAGE
		self.title = None
		
	def setMsg(self, msg):
		self.WARNING_MESSAGE = msg
	
	def setTitle(self, title):
		if title != None:
			self.title = title
	
	def run_from_thread(self):
		gobject.timeout_add(0, self.run)
	
	def run(self):
		#Create the dialog box and assign the iconview
		self.wTree = gtk.glade.XML(gladeFile, "dialog3")
		self.lab = self.wTree.get_widget("warningLabel")
		self.lab.set_label(self.WARNING_MESSAGE)
		self.dlg = self.wTree.get_widget("dialog3")
		if self.title != None:
			self.dlg.set_title(self.title)
		self.input = self.dlg.run()
		
		#Check if user selected OK
		if self.input == gtk.RESPONSE_OK:
			self.dlg.destroy() 
		self.dlg.destroy()
