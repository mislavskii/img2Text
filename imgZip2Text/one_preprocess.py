import zipfile
from time import time
from imgzip2text import preprocess, get_paths

path, save_path = get_paths()

name = input('Individual image to process: ')

threshold = input('Threshold method or value (skip to use default): ')

start = time()
if path.endswith('zip'):
    with zipfile.ZipFile(path) as imgzip:
        with imgzip.open(name) as cur:
            im = preprocess(cur, threshold=threshold)
else:
    im = preprocess(path + name, threshold)
im.save(save_path + '/' + str(threshold) + '_' + name)
print(f'saved to {save_path}', end='\n\n')

print(f'Done in {round(time() - start, 1)} seconds.')
