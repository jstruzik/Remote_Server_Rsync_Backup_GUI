#Variables
from time import strftime
from uuid import getnode as get_mac
time = strftime("%m_%d_%y_%M_%S")
mac = get_mac()
global_log_file = "/tmp/"+str(mac)+"_backup_"+time+".log"
lockfile = '/tmp/backup.lock'
default_log_level = "DEBUG"
gladeFile = "backupgui.glade"
REMOTE_PATH = '/path/'
REMOTE_BACKUP_SERVER = 'server'
