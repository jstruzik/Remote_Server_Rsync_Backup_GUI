#!/usr/bin/env python
# encoding: utf-8
import os, re

#This handles the final filter file generation.
#This class was taken more or less directly from Curtis Minns' original script.
class rsyncfilter:
	def __init__( self, ffile ):
		self.ffile = ffile
		self.extensions = []
		self.files = []
		self.directories = []
		folders = False
		extensions = False
		files = False
		EXCLUDES = open('./excludes_list','r')
		
		for line in EXCLUDES:
			if '#####Folders#####' in line:
				folders = True
				continue
			elif '#####Extensions#####' in line:
				extensions = True
				folders = False
				continue
			elif '#####Files#####' in line:
				files = True
				folders = False
				extensions = False
				continue
			if folders:
				self.directories.append(line)
			if extensions:
				self.extensions.append(line)
			if files:
				self.files.append(line)

	
	def add( self, path ):
		#if not os.path.exists( path ):
		#	sys.exit("Something went wrong, this path doesn't exist: " + path)
		FILTER = open( self.ffile, 'a' )
		if os.path.isdir( path ): # Only do this if 'path' is a dir, can't explore a file like a dir....
			for d in os.listdir( path ):
				if re.match( 'windows|winnt', d, re.I ):
					winner = False
					for w in os.listdir( path + '/' + d ):
						if re.match( '^(desktop|favorites|profiles|application data)$', w, re.I ):
							FILTER.writelines( '+ ' + path.replace( ' ', '?' ) + '/' + d.replace( ' ', '?' ) + '/' + w.replace( ' ', '?' ) + '/***\n' )
							winner = True
					if winner:
						FILTER.writelines( '- ' + path.replace( ' ', '?' ) + '/' + d.replace( ' ', '?' ) + '/*\n' )
					else:
						FILTER.writelines( '- ' + path.replace( ' ', '?' ) + '/' + d.replace( ' ', '?' ) + '/\n' )
				if re.match( 'progra', d, re.I ):
					FILTER.writelines( '- ' + path.replace( ' ', '?' ) + '/' + d.replace( ' ', '?' ) + '/\n' )
		FILTER.close()
	
	#This adds an include line to our excludes file.
	def include( self, path ):
		FILTER = open( self.ffile, 'a' )
		FILTER.writelines( '+ ' + path.replace( ' ', '?' ) + '/***\n' )
		FILTER.close()
	
	#This simply makes all the excluded extensions, files, and directories case insensitive with regular expressions.
	def out( self ):
		FILTER = open( self.ffile, 'a' )
		for item in self.extensions:
			item = item.lower().replace( ' ', '?' )
			FILTER.writelines( '- *.' + re.sub( r'([a-z])', lambda m: '[' + m.group(0).upper() + m.group(0) + ']', item ) + '\n' )
		for item in self.files:
			item = item.lower().replace( ' ', '?' )
			FILTER.writelines( '- ' + re.sub( r'([a-z])', lambda m: '[' + m.group(0).upper() + m.group(0) + ']', item ) + '\n' )
		for item in self.directories:
			item = item.lower().replace( ' ', '?' )
			FILTER.writelines( '- ' + re.sub( r'([a-z])', lambda m: '[' + m.group(0).upper() + m.group(0) + ']', item ) + '/\n' )
		FILTER.close()
