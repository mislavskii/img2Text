import zipfile
from time import time
from imgzip2text import preprocess, get_paths, thumbsheet

path, save_path = get_paths()

print('Building thumbsheet...')
thumbsheet(path, resize_factor=14).save(save_path + '/' + 'sheet.jpg')

threshold = input('Threshold method or value (skip to use default): ')

print('Processing images:', end='\n\n')
start = time()
with zipfile.ZipFile(path) as imgzip:
    for name in imgzip.namelist():
        print(f'{imgzip.namelist().index(name) + 1} of {len(imgzip.namelist())}: {name}')
        with imgzip.open(name) as cur:
            im = preprocess(cur, threshold=threshold)
            im.save(save_path + '/' + name)
            print(f'saved to {save_path}', end='\n\n')

print(f'Done in {round(time() - start, 1)} seconds.')
