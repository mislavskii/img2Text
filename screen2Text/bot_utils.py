from io import BytesIO

from PIL import Image

from screen2text import DictLookup as dlp
import requests as rq


def do_recognize(file):
    r = rq.get(file.file_path)
    im = Image.open(BytesIO(r.content))
    x = dlp()
    x.load_image(im)
    x.threads_recognize(lang='tha', kind='word')
    x.generate_suggestions()
    return x.suggestions

