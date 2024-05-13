from PIL import ImageGrab
import pytesseract
import requests as rq
from bs4 import BeautifulSoup as bs
from IPython.display import display
from IPython.display import HTML
import threading
from datetime import datetime as dt
from pythainlp import spell, correct
import os
import pandas as pd

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

    @staticmethod
    def get_freqs(strings):
        """
        takes a collection of :strings: and returns a list of tuples mapping strings to their relative frequencies,
        sorted in descending order
        """
        freqs = {}
        for word in strings:
            freqs[word] = freqs.get(word, 0) + 1
        total = sum(freqs.values())
        for key, val in freqs.items():
            freqs[key] = round(val / total, 2)
        return sorted(freqs.items(), key=lambda item: item[1], reverse=True)

    def __init__(self):
        self.suggestions = []
        self.im = None
        self.bim = None
        self.out_texts = {}
        self.bims = {}
        self.validated_words = {}
        if not os.path.exists('bims'):
            os.mkdir('bims')

    def grab(self):
        self.bim = None
        im = ImageGrab.grabclipboard()
        if im:
            self.im = im  # .convert("L")
        else:
            print('Looks like there was no image to grab. Please check the clipboard contents!')
            return

    def load_image(self, pil_image):
        self.im = pil_image

    def binarize(self, skew=1.0):
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

    def recognize_bin(self, skew=1.0, lang='tha', config='--psm 7'):
        return pytesseract.image_to_string(self.binarize(skew), config=config, lang=lang).strip()

    def fan_recognize_bin(self, lang='tha'):
        for code in list(self.config_dict.keys())[3:]:
            for skew in list(range(75, 140, 5)):
                key = code * 1000 + skew
                self.out_texts[key] = self.recognize_bin(skew / 100, lang=lang, config=f'--psm {code}')

    def fan_recognize(self, lang, psm):
        """For given psm value, recognizing original image and binarized in a range of threshold skews
        from self.bims, which will have to be already prepared to avoid repeated binarization
        in concurrent recognizing"""
        self.out_texts[psm] = self.recognize_original(lang=lang, config=f'--psm {psm}')
        for skew, image in self.bims.items():
            key = psm * 1000 + skew
            self.out_texts[key] = pytesseract.image_to_string(image, lang=lang, config=f'--psm {psm}').strip()
        # print(len(self.out_texts))

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
        """
        checks recognition results gathered in out_texts against corpus.
        """
        self.validated_words.clear()
        with open(self.corpus_path, encoding='utf-8') as corpus:
            lexicon = corpus.readlines()
            for key, text in self.out_texts.items():
                if text and len(text) > 1:
                    for entry in lexicon:
                        if text in entry:
                            self.validated_words[key] = text

    def generate_suggestions(self):
        self.validate_words()
        self.suggestions = self.get_freqs(self.validated_words.values())
        out_text_freqs = self.get_freqs([item for item in self.out_texts.values() if item and '\n' not in item])
        if self.suggestions:
            leader = self.suggestions[0][0]
            leader_general_score = {item[0]: item[1] for item in out_text_freqs}[leader]
            mean_score = sum([item[1] for item in self.suggestions]) / len(self.suggestions)
            enrichment_floor = min(mean_score, leader_general_score)
            noise_ceiling = self.suggestions[0][1] * .04
            self.suggestions = [item for item in self.suggestions if item[1] > noise_ceiling]
        else:
            enrichment_floor = 0.01
        candidate_cap = 3
        top_texts = out_text_freqs[:candidate_cap
                    ] if len(out_text_freqs) > candidate_cap else out_text_freqs
        for candidate in top_texts:
            if candidate[0] not in [item[0] for item in self.suggestions] and candidate[1] > enrichment_floor:
                self.suggestions.append(candidate)
                corrected = correct(candidate[0])
                if corrected not in [item[0] for item in self.suggestions]:
                    self.suggestions.append((corrected, -1))
        self.suggestions.sort(key=lambda item: item[1], reverse=True)

    def inspect_results(self):
        if not self.im:
            return
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


class DictLookup(ClipImg2Text):
    dic_url = 'https://dict.longdo.com/search/'

    def __init__(self):
        super().__init__()
        self.word = None
        self.soup = None

    def lookup(self, word):
        self.word = word
        response = None
        attempts = 3
        print(f'Looking up {word}... ', end='')
        while attempts:
            try:
                response = rq.get(self.dic_url + word, timeout=15)
                break
            except:
                attempts -= 1
                print(' * ', end='')
                continue
        print()
        if not response or response.status_code != 200:
            print("Couldn't fetch.")
            return
        response.encoding = 'utf-8'
        self.soup = bs(response.text, features="lxml")

    def output_html(self):
        headers = self.soup.find_all('td', attrs={'class': 'search-table-header'})
        tables = self.soup.find_all('table', attrs={'class': 'search-result-table'})
        style = '''<style>table {width: 60%;} </style>'''
        content = f'<h4>Lookup results for "<strong>{self.word}</strong>"</h4>'
        for header, table in zip(headers, tables):
            text = header.text
            if not ('Subtitles' in text or 'German-Thai:' in text or 'French-Thai:' in text):
                content += f'<h5>{header.text}</h5>\n'
                content += str(table).replace("black", "white") + '\n'

        with open('html/template.html', 'r', encoding='utf-8') as template:
            html = template.read()

        with open('html/out.html', 'w', encoding='utf-8') as out:
            out.write(html.replace('%content%', content))

        display(HTML(style + content))

    def recognize_and_lookup(self, lang='tha', kind=None, output='html'):
        self.grab()
        if not self.im:
            return
        display(self.im)
        start = dt.now()
        self.threads_recognize(lang, kind)
        print(f'Done in {dt.now() - start}')
        self.generate_suggestions()
        if not self.suggestions:
            print('No meaningful recognition results could be obtained from the image')
            return
        top = self.suggestions[0]
        best_guess = f'The best guess is "{top[0]}" rated {top[1]}\n'
        others = 'Others:\n'
        for i in range(1, len(self.suggestions)):
            other = self.suggestions[i]
            others += f'{i} - {other[0]} ({other[1]})\t'
        word = input(
            f'''{best_guess}{others}\n
            Enter to proceed with top-rated suggestion or number for other or any desired word:'''
        )
        if not word:
            self.lookup(top[0])
        else:
            try:
                self.lookup(self.suggestions[int(word)][0])
            except:
                self.lookup(word)
        if output == 'html':
            self.output_html()


print('>> screen2text imported.')
