import sys, os, subprocess,re,logging
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

#Creates a new filechooser
class fileChooser:
	def __init__(self, FOLDERS, gf = gladeFile):
		self.logger = logging.getLogger(__name__)
		self.gladefile = gf
		self.li = []
		self.FOLDERS = FOLDERS
		
	def run(self):
		self.wTree = gtk.glade.XML(self.gladefile, "filechooserdialog1")
		self.fc = self.wTree.get_widget("filechooserdialog1")
		self.input = self.fc.run()
		
		#Grab the folder names and add them to our list
		for folders in self.fc.get_filenames():
			self.li.append(folders)
		
		#If user selects Ok (-5 for some bizarre reason)
		if self.input == -5:
			#Make sure folders were selected
			if len(self.li)>0:
				self.fc.destroy()
				self.FOLDERS = True
				return self.li,self.FOLDERS
		else:
			self.fc.destroy()
			self.FOLDERS = False
			return None,self.FOLDERS
		
		#Closes window
		self.fc.destroy()
