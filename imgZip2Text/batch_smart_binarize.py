# Takes a zip archive of images, binarizes them,
# also cleans margins and rotates to portrait if necessary
import time
import zipfile
from imgzip2text import load_image, smart_binarize_as_array

floc = input('File location: ').replace('\\', '/')
if not floc.endswith('/') and not floc.endswith('zip'):
    floc = floc + '/'
print(floc)
fname = input('File name: ')
path = floc + fname
print(path)

start = time.time()
with zipfile.ZipFile(path) as imgzip:
    for name in imgzip.namelist():
        print(f'processing {imgzip.namelist().index(name) + 1} of {len(imgzip.namelist())}: {name}')
        with imgzip.open(name) as cur:
            im = load_image(cur)
            im = smart_binarize_as_array(im, edges=False)
            save_path = 'smartbin/' + fname.rstrip('.zip') + '_' + name
            im.save(save_path)
            print(f'saved as {save_path}', end='\n\n')

print(f'Done in {round(time.time() - start, 1)} seconds.')
