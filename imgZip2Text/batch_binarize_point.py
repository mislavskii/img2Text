# Takes a zip archive of images, binarizes them,
# also cleans margins and rotates to portrait if necessary

import zipfile
from PIL import Image
import time
from imgzip2text import clean_margins  # , binarize


def binarize(x):
    """Utility function to change pixel value to O (black) or 255 (white) over the threshold
    Used as :lut: parameter value in Image.point method to binarize an image"""
    return 0 if x < threshold else 255


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
            im = Image.open(cur).convert('L')
            threshold = sum(im.getextrema()) // 2.3
            print(im.getextrema(), threshold)
            im = im.point(lut=binarize).convert('1', dither=0)
            if im.width > im.height:
                im = im.rotate(270, expand=True)
            im = clean_margins(im)
            save_path = path.rstrip('.zip') + '/' + name
            im.save(save_path)
            print(f'saved as {save_path}', end='\n')

print(f'Done in {round(time.time() - start, 1)} seconds.')
