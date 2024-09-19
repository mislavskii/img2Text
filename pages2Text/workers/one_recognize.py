from imgzip2text import Image2Text

recog = Image2Text(image=input('Full path to the image file: '),
                   pre=input('Preprocess? (any/enter)'),
                   binarize=input('Binarize? (any/enter)')
                   )
segment = input('Segment? (any/enter)')
if segment:
    recog.recognize_by_lines()
else:
    lang = input('Language (tha/eng/rus.../enter) ')
    if not lang:
        lang = 'tha'
    recog.recognize_as_is(lang)

recog.save_to_file()

# F:\User\Learn\Skillbox\WebDev2.0\2\Таблица.jpg
# F:\User\Earn\Translate\Thai\LINGVO Connect\Прайвет\page4\TI4Obj2.tiff
