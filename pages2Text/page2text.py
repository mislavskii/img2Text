from PIL import Image, ImageDraw
import pytesseract

from pages2Text.preprocessing import binarize_as_array, preprocess

# tess_path = 'C:/Program Files/Tesseract-OCR/tesseract.exe'
tess_path = r'C:\Users\User\AppData\Local\Tesseract-OCR\tesseract.exe'
pytesseract.pytesseract.tesseract_cmd = tess_path
# TESSDATA_PREFIX = r'C:/Program Files/Tesseract-OCR/tessdata'
TESSDATA_PREFIX = 'C:/Users/User/AppData/Local/Tesseract-OCR/tessdata'


# TEXT RECOGNITION (WITH TESSERACT)

def segment(im,
            threshold=.0009,  # minimal proportion of black pixels in a row for it to qualify as a dark one
            gap=1,  # minimal gap between lines of text in pixels
            line_height_cap=0.2  # max height of text line relative to image height (to skip large objects)
            ):
    """returns a list of text line boxes, each as a four-tuple defining x, y for left upper and right bottom corners.
    needed dependencies:
    - PIL.Image[,
    - PIL.ImageDraw - only to display image with text boxes on it]"""

    # Finding rows with proportion of black pixels above the threshold value ('dark rows')
    dark_rows = []
    left = 0
    right = im.width
    for y in range(im.height):
        black = 0
        for x in range(left, right):
            if im.getpixel((x, y)) == 0:
                black += 1
        if black / (right - left) > threshold:
            dark_rows.append(y)
    # Identifying lines of text as bands where dark rows are closer to each other than the gap value
    # and adding the pad value at top and bottom of each line
    text_lines = []
    pad = gap * 2
    top = dark_rows[0]
    for i in range(1, len(dark_rows)):
        if dark_rows[i] - dark_rows[i - 1] > gap:
            bottom = dark_rows[i - 1]
            text_lines.append((top - pad, bottom + pad))
            top = dark_rows[i]
    if dark_rows[-1] - top > pad:
        text_lines.append((top - pad, dark_rows[-1] + pad))
    # preparing crop boxes for each detected text line:
    boxes = []
    # visualizing text lines as crop boxes on the image
    # and storing crop boxes to the list
    draw = ImageDraw.Draw(im)
    for line in text_lines:
        box = (left, line[0], right, line[1])
        if line[1] - line[0] < im.height * line_height_cap:  # large pictures won't pass
            draw.rectangle(box, fill=None, width=2, outline=0)
            boxes.append(box)

    return im, boxes


# TODO: Rewrite the **segment** function using numpy array (and some other improvements)
# TODO: Teach it to avoid pictures but keep the sideways text lines


class Image2Text:

    def __init__(self, image: Image, pre=False, binarize=False):
        """Loads an image file to be recognized.
        :image: PIL Image object
        :pre: loads image with preprocessing if selected, default False
        :bin: loads image with binarization if selected, default False
        """
        self.bim = None
        self.boxes = []
        self.boxed_im = None
        self.crops = []
        self.lines = []
        self.text = ''
        if pre:
            print('Loading image with full preprocessing')
            self.im = preprocess(image)
        elif binarize:
            print('Loading image with binarization only')
            self.im = binarize_as_array(image)
        else:
            print('Loading image with no preprocessing')
            self.im = image

    def binarize(self, threshold=None, t_factor=1):
        self.bim = binarize_as_array(self.im.convert('L'), threshold, t_factor)

    def recognize_as_is(self, lang=None):
        if not lang:
            lang = input('Recognition language(s): ')
        self.text = pytesseract.image_to_string(self.im, lang=lang)
        print('Recognition with no segmentation completed.')

    def recognize_by_lines(self):
        """
        Gets bounding boxes for each line of text superimposing them on the image to keep separately as `self.boxed_im`,
        crops each box from the image appending it to `self.crops`, and recognizes
        as a single line appending the obtained string to `self.lines`
        """
        self.boxed_im, self.boxes = segment(self.bim)
        lang = input('Recognition language(s): ')
        if not lang:
            lang = 'tha'
        for box in self.boxes:
            crop = self.bim.crop(box)
            self.crops.append(crop)
            line = pytesseract.image_to_string(crop, config='--psm 7', lang=lang)
            self.lines.append(line)
        self.text = ''.join(self.lines)
        print('Recognition with segmentation completed.')

    def save_to_file(self, save_path):
        """Saving recognition results to text file named as per `save_path` + txt extension"""
        save_path = save_path + '.txt'
        with open(save_path, 'w', encoding='utf-8') as file:
            file.write(self.text)
        print(f'saved to {save_path}', end='\n\n')
