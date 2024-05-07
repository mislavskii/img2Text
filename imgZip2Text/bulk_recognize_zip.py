# Recognizing images from zip archive with optional preprocessing
import zipfile
from time import time
from imgzip2text import preprocess, get_paths, load_image
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Users\Maksim Mislavskii\AppData\Local\Tesseract-OCR\tesseract.exe'

# import sqlite3

path, save_path = get_paths()
pre = False
print('Processing images:', end='\n\n')
start = time()
with zipfile.ZipFile(path) as imgzip:
    for name in imgzip.namelist():
        print(f'{imgzip.namelist().index(name) + 1} of {len(imgzip.namelist())}: {name}')
        with imgzip.open(name) as cur:
            if pre:
                im = preprocess(cur)
            else:
                im = load_image(cur)
            text = pytesseract.image_to_string(im,
                                               lang='tha',
                                               config='--psm 4'
                                               )
            print(text, end='\n' * 2)

print(f'Done in {round(time() - start, 1)} seconds.')
