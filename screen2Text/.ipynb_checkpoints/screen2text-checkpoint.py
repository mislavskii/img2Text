from PIL import Image
from PIL import ImageGrab
import pytesseract
import requests as rq
from bs4 import BeautifulSoup as bs
from IPython.display import display
from IPython.display import HTML
import threading
from datetime import datetime as dt

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


class ClipImg2Text:
    config_codes = """  0    Orientation and script detection (OSD) only.
      1    Automatic page segmentation with OSD.
      2    Automatic page segmentation, but no OSD, or OCR.
      3    Fully automatic page segmentation, but no OSD. (Default)
      4    Assume a single column of text of variable sizes.
      5    Assume a single uniform block of vertically aligned text.
      6    Assume a single uniform block of text.
      7    Treat the image as a single text line.
      8    Treat the image as a single word.
      9    Treat the image as a single word in a circle.
     10    Treat the image as a single character.
     11    Sparse text. Find as much text as possible in no particular order.
     12    Sparse text with OSD.
     13    Raw line. Treat the image as a single text line, bypassing hacks that are Tesseract-specific."""
    config_dict = {int(entry[0]): entry[1] for entry in
                   [entry.strip().split('    ') for entry in config_codes.split('\n')]}
    corpus_path = r'F:\User\Learn\ไทยศึกษา\Linguistics\lexitron_thai.txt'

    def __init__(self):
        self.bim = None
        self.im = None
        self.out_texts = {}
        self.validated_words = {}

    def grab(self):
        self.bim = None
        im = ImageGrab.grabclipboard()
        if im:
            self.im = im  # .convert("L")
        else:
            print('Looks like there was no image to grab. Please check the clipboard contents!')

    def load_image(self, pil_image):
        self.im = pil_image

    def binarize(self, skew=1):
        im = self.im.copy().convert("L")
        lightness = len(im.getdata()) / sum(im.getdata())
        threshold = sum(im.getextrema()) / 2 * skew
        xs, ys = im.size
        for x in range(xs):
            for y in range(ys):
                if im.getpixel((x, y)) > threshold:
                    px = 255  # if lightness > 0.25 else 0
                else:
                    px = 0  # if lightness > 0.25 else 255
                im.putpixel((x, y), px)
        return im

    def fan_binarize(self):
        self.bims = {}
        for skew in range(50, 150, 5):
            bim = self.binarize(skew / 100)
            bim.save(f'bims/{skew}.png')
            self.bims[skew] = bim

    def recognize_original(self, lang='tha', config='--psm 7'):
        return pytesseract.image_to_string(self.im, config=config, lang=lang).strip()

    def fan_recognize_original(self, lang='tha'):
        for code in list(self.config_dict.keys())[3:]:
            try:
                self.out_texts[code] = self.recognize_original(lang=lang, config=f'--psm {code}')
            except Exception as e:
                # texts[code] = e.__str__()
                continue

    def recognize_bin(self, skew=1, lang='tha', config='--psm 7'):
        return pytesseract.image_to_string(self.binarize(skew), config=config, lang=lang).strip()

    def fan_recognize_bin(self, lang='tha'):
        for code in list(self.config_dict.keys())[3:]:
            for skew in list(range(75, 140, 5)):
                key = code * 1000 + skew
                self.out_texts[key] = self.recognize_bin(skew / 100, lang=lang, config=f'--psm {code}')

    def fan_recognize(self, lang, psm):
        """For given psm value, recognizing original image and binarized in a range of threshold skews
        from self.bims, which will have to be already prepared"""
        self.out_texts[psm] = self.recognize_original(lang=lang, config=f'--psm {psm}')
        for skew, image in self.bims.items():
            key = psm * 1000 + skew
            self.out_texts[key] = pytesseract.image_to_string(image, lang=lang, config=f'--psm {psm}').strip()
        print(len(self.out_texts))

    def threads_recognize(self, lang, kind=None):
        """Recognizing the image, both original and binarized, in a range of psm values as per :kind:,
        appying a range of threshold skews as defined in `fan_recognize` run in a separate thread 
        for each psm value 
        """
        self.fan_binarize()
        lang = lang
        self.out_texts.clear()
        psms = list(self.config_dict.keys())[3:]
        psms.insert(0, 1)
        if kind == 'block':
            psms = (1, 3, 4, 6, 11, 12, 13)
        if kind == 'line':
            psms = (1, 3, 4, 6, 7, 11, 12, 13)
        threads = [threading.Thread(target=self.fan_recognize, args=(lang, psm), name=f't_{psm}') for psm in psms]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

    def validate_words(self):
        self.validated_words.clear()
        with open(self.corpus_path, encoding='utf-8') as corpus:
            lexicon = corpus.readlines()
            for key, text in self.out_texts.items():
                if text and len(text) > 1:
                    for entry in lexicon:
                        if text in entry:
                            self.validated_words[key] = text
        freqs = {}
        for word in self.validated_words.values():
            freqs[word] = freqs.get(word, 0) + 1
        total = sum(freqs.values())
        for key, val in freqs.items():
            freqs[key] = round(val / total, 2)
        return dict(sorted(freqs.items(), key=lambda item: item[1], reverse=True))

    def inspect_results(self):
        display(self.im)
        for key, text in sorted(self.out_texts.items(), key=lambda item: item[0]):
            if key <= 13:
                print(f'{key}:', text.replace('\n', ''), end=', ')
        print()

        print(f"\n{self.im.getextrema()} -> {self.im.convert('L').getextrema()}")
        for skew, image in self.bims.items():
            print(f'\n{skew / 100}')
            display(image)
            for key, text in sorted(self.out_texts.items(), key=lambda item: item[0]):
                if str(key).endswith(str(skew)):
                    print(f'{key // 1000}:', text.replace('\n', ''), end=', ')
            print()


print('>> screen2text imported.')
