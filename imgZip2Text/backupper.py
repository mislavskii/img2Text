"""Backups a file (imgzip2text.py by default) to backup directory with adding date and time to the file name"""

from datetime import datetime as dt

file_name = input('File name: ')
if not file_name:
    file_name = 'imgzip2text.py'

with open(file_name, 'r') as f:
    now = str(dt.now()).replace(' ', '_').replace(':', '-').split('.')[0]
    backup_name = file_name.replace('.', '_' + now + '.')
    backup_data = f.read()

backup_path = 'backup/' + backup_name

with open(backup_path, 'w') as f:
    f.write(backup_data)

print('Backup completed to', backup_path)
