from imgzip2text import load_image, smart_binarize_as_array
from time import time

name = 'IMG_4869.jpg'
im = load_image(name)
# if im.height < im.width: im = im.rotate(270, expand=1)
im = smart_binarize_as_array(im)
print()
im.save('smartbin/' + name.replace('.', '_' + str(int(time())) + '.'))
print('Done.')
