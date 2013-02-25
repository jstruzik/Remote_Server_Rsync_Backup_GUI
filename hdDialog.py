import sys, os, subprocess,re, logging
from time import sleep
from fileChooser import fileChooser
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
	
icon = gtk.STOCK_HARDDISK

#Class for the HD selector window
class hdDialog:
	
	def __init__(self, BUTTON_SWITCH,FOLDERS,gf=gladeFile):
		self.logger = logging.getLogger(__name__)
		self.gladefile = gf
		self.BUTTON_SWITCH = BUTTON_SWITCH
		self.FOLDERS = FOLDERS
		self.folders_selected=[]
		
	def run(self):
		#Create the dialog box and assign the iconview
		self.wTree = gtk.glade.XML(self.gladefile, "dialog2")
		self.dlg = self.wTree.get_widget("dialog2")
		self.hd = self.wTree.get_widget("iconview1")
		button9 = self.wTree.get_widget("button9")
		
		#Turns the 'Individual Folder' button on or off
		if self.BUTTON_SWITCH:
			button9.hide()
		else:
			button9.show()
		
		#Setup our small little dictionary
		dic = { "on_button9_clicked" : self.button9_clicked}
		self.wTree.signal_autoconnect(dic)
		
		#Create a store of text and icons for the iconview to use
		liststore = gtk.ListStore(str, gtk.gdk.Pixbuf)
		self.hd.set_model(liststore)
		#Assign which column the text and icons use
		self.hd.set_text_column(0)
		self.hd.set_pixbuf_column(1)
		
		#Initiate list to hold selection number which later is converted to
		#a drive name
		li=[]
		
		#Loop through system drives and assign each a name/icon
		for dir in os.listdir('/media/'):
			li.append(dir)
			size = os.statvfs('/media/'+dir)
			cap = ((size.f_bsize * size.f_blocks) / (1024*1024)/1024.0)
			final = dir + " (" + str(round(cap,2)) + " GB)"
			pixbuf = self.hd.render_icon(icon, gtk.ICON_SIZE_LARGE_TOOLBAR)
			liststore.append([final,pixbuf])
		
		
		self.input = self.dlg.run()
		
		#Check if user selected OK
		if self.input == gtk.RESPONSE_OK:
			
			#Make sure a drive actually exists
			if len(li)>0:
				#Assign selected drive
				self.name = self.hd.get_selected_items()
				#Loop through drives and ensure there was a selection
				for select in self.name:
					if self.hd.path_is_selected(select)==True:
						if not self.BUTTON_SWITCH:
							self.FOLDERS = False
						#Convert return list to integer and then string
						s = filter(str.isdigit, repr(self.name))
						t = int(s)
						self.dlg.destroy()
						#Return the input of the user as well as the drive
						if self.FOLDERS:
							if self.BUTTON_SWITCH:
								return self.input,li[t],self.FOLDERS
							else:
								return self.input,li[t],self.FOLDERS,self.folders_selected
						else:
							if self.BUTTON_SWITCH:
								return self.input,li[t],self.FOLDERS
							else:
								return self.input,li[t],self.FOLDERS,None
				
		
		#Closes window
		self.dlg.destroy()
		
		if self.FOLDERS:
			if self.BUTTON_SWITCH:
				return self.input,"",self.FOLDERS
			else:
				return self.input,"",self.FOLDERS,self.folders_selected
		else:
			if self.BUTTON_SWITCH:
				return self.input,"",self.FOLDERS
			else:
				return self.input,"",self.FOLDERS,None
		
	#Builds our filechooser dialog
	def button9_clicked(self, widget):
		fc =fileChooser(self.FOLDERS)
		self.folders_selected,self.FOLDERS = fc.run()
