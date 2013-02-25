#!/usr/bin/env python

import sys, os, subprocess,re,copy
from time import sleep
from re import match

def parse_BLKID():
	# Grab output from command "blkid" and split it up by device
	blkid = subprocess.Popen("blkid", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()[0]
	blkid = blkid.split("\n")
	blkid = [item.split() for item in blkid]

	# Last element of blkid is empty or unnecessaary, so strip it out
	blkid = blkid[:len(blkid)-1]

	# Create a list of dictionaries for the devices, excluding UUIDs
	# Do we need to store the UUIDs? It may be a good idea....
	partitions = []
	for element in blkid:
		partitions.append({})
		for info in element:
			if '/dev/' in info:
				partitions[len(partitions)-1]['dev'] = info[:len(info)-1]
			if 'TYPE' in info:
				partitions[len(partitions)-1]['type'] = info[info.find('=')+2:len(info)-1]
			if 'LABEL' in info:
				partitions[len(partitions)-1]['label'] = info[info.find('=')+1:]

	# Strip out any partitions with a type that isn't in the regex pattern below
	# or that are loopback devices
	temp = copy.deepcopy(partitions)

	for i in temp:
		if not match("ext|[hjx]fs|ntfs|fat|reiser|vfat", i['type']) or '/dev/loop' in i or '/dev/mapper' in i['dev']:
			partitions.remove(i)
	return partitions

def parse_mtab(blkid_list):
	# Try opening the mtab file to see what's mounted
	os.system( 'cat /etc/mtab' )
	mtab_lines = []
	# The only thing that should be in the 'try' block should be the 'open' call, 
	# as that should be the only exception it's catching (and if it fails, we should exit).
	try:
		mtab_file = open('/etc/mtab', 'r')
	except:
		sys.exit("Error reading '/etc/mtab'. Exiting.")
	for line in mtab_file.readlines():
		split_line = line.split()
		# If this was not run as root, blkid_list was empty
		# which caused 'in_haystack' to fail.
		if in_haystack(split_line[0], blkid_list):
			mtab_lines.append(split_line)
	return mtab_lines
	
# Search 'haystack' (a list of dictionaries or lists) for 'needle'
# Returns True if found, False if not
def in_haystack(needle, haystack):
	if type(haystack[0]).__name__=='dict':
		for element in haystack:
			if needle in element.values():
				return True
		return False
	if type(haystack[0]).__name__=='list':
		for element in haystack:
			if needle in element:
				return element
		return 0

def mark_partitions(parts, m_parts):
	for element in parts:
		search_result = in_haystack(element['dev'], m_parts)
		if search_result == 0:
			element['mounted'] = 0
		else:
			element['mounted'] = 1
			element['mount_point'] = search_result[1]
	return parts

def mount(part):
	# Use the partition label as the mount point if available
	if part.has_key('label'):
		label = part['label'].strip('"')
		mount_dir = '/media/' + label
	# Otherwise, use the device identifier (e.g. 'sda1')
	else:
		mount_dir = part['dev'].split('/')
		mount_dir = '/media/' + mount_dir[ len(mount_dir) - 1 ]
	
		if os.path.isdir(mount_dir):
			counter = 1
			mount_dir += str(counter)
			while os.path.isdir(mount_dir):
				counter += 1
				mount_dir = mount_dir[:-1]
				mount_dir += str(counter)

	# Create the mount point under /media
	os.system('sudo ' + 'mkdir -p ' + mount_dir)

	# If it's an NTFS partition, use 'ntfs-3g' to mount it
	if part['type'] == 'ntfs':
		result = os.system("sudo " + "ntfs-3g " + part['dev'] + " " + mount_dir + " -o noatime,nosuid,nodev,utf8,remove_hiberfile,force")
	# Otherwise mount it regularly
	else:
		result = os.system("sudo " + "mount " + part['dev'] + " " + mount_dir + " -o rw,nosuid,nodev,uid=1000,gid=1000,shortname=mixed,dmask=0077,utf8=1,showexec,flush")
	# If it mounted correctly, report it as such.
	if result == 0:
		print "Mounted " + part['dev'] + " (" + part['type'] + ") at " + mount_dir
	else:
		print "Mounting error occurred! Exiting."
def autoMount():
	# Get available partitions from command 'blkid'
	all_parts = parse_BLKID()
	if all_parts == []:
		print "No partitions found...."
		return
	# Get a list of mounted partitions from the /etc/mtab file
	mounted_partitions = parse_mtab(all_parts)

	# Put 'partitions' and 'mounted_partitions' together
	# and place a key in each 'partitions' element to mark mount status [0/1]
	partitions = mark_partitions(all_parts, mounted_partitions)
	for part in partitions:
		if part['mounted'] == 0:
			mount(part)
			
if __name__ == '__autoMount__':
	autoMount()
