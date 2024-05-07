"""
rewriting the Image2Text class for greater flexibility
"""

import os
from PIL import Image, ImageDraw
import numpy as np
from skimage.filters import *
import zipfile
import pytesseract

# tess_path = 'C:/Program Files/Tesseract-OCR/tesseract.exe'
tess_path = r'C:\Users\User\AppData\Local\Tesseract-OCR\tesseract.exe'
pytesseract.pytesseract.tesseract_cmd = tess_path
# TESSDATA_PREFIX = r'C:/Program Files/Tesseract-OCR/tessdata'
TESSDATA_PREFIX = 'C:/Users/User/AppData/Local/Tesseract-OCR/tessdata'

# NOTATION NOTE -  as applied to variable/parameter names in the code below:
# 'image' refers to a general image file
# 'im' refers to a PIL image object


# noinspection PyShadowingNames
def thumbsheet(file,
               sheet_width=900,
               resize_factor=20,
               margin=3
               ):
    """
    Builds a thumbsheet of all images from zip archive
    :type margin: int
    :param file: zip file location as full path string or file name
    :param sheet_width: desired width of the thumbsheet in pixels
    :param resize_factor: divides original image size by this value to get thumbnail size
    :param margin: margin at thumbsheet edges in pixels
    :return: thumbsheet as a PIL.Image object
    """
    with zipfile.ZipFile(file) as imgzip:
        # Calculating the thumbsheet height
        sheet_height = margin
        row_height = margin
        row_length = margin
        for name in imgzip.namelist():
            with imgzip.open(name) as cur:
                im = Image.open(cur)
                # im.save(name)
                x, y = im.width // resize_factor, im.height // resize_factor
                if y > row_height:
                    row_height = y + margin
                if row_length + x > sheet_width - margin:
                    row_length = (x + margin)
                    sheet_height += row_height
                    row_height = (y + margin)
                else:
                    row_length += (x + margin)
        sheet_height += row_height
        # Creating the thumbsheet
        sheet = Image.new('L', (sheet_width, sheet_height))
        # Pasting thumbsized images on the thumbsheet
        cur_x = margin
        cur_y = margin
        row_height = 0
        for name in imgzip.namelist():
            with imgzip.open(name) as cur:
                im = Image.open(cur)
                x, y = int(im.width / resize_factor), int(im.height / resize_factor)
                if y > row_height:
                    row_height = y
                im = im.resize((x, y))
                if cur_x + x > sheet_width - margin:
                    cur_y += (row_height + margin)
                    cur_x = margin
                sheet.paste(im, (cur_x, cur_y))
                cur_x += (x + margin)
    return sheet


def get_paths():
    # Getting the archive to process
    floc = input('File location: ').replace('\\', '/')
    if floc and not floc.endswith('/') and not floc.endswith('zip'):
        floc = floc + '/'
    print(floc)
    if not floc.endswith('zip'):
        fname = input('Archive file name (skip if image not in an archive): ')
        path = floc + fname
    else:
        path = floc
    if not path:
        print('Nothing to process. See you later!')
        exit()
    print(path)
    # Preparing the output folder
    save_path = path.rstrip('.zip')
    if not os.path.exists(save_path):
        os.mkdir(save_path)
    return path, save_path


# IMAGE PREPROCESSING
# TODO: Clean the needless functions in this section

def load_image(image, mode='L'):
    """Loads image from file, returns a PIL image object in 'L' mode (b/w)
    (output mode can be changed if necessary)"""
    im = Image.open(image).convert(mode)
    return im


def small(im, factor=12):
    """Takes a PIL image object, returns a copy reduced in size by :factor:"""
    return im.convert('L').reduce(factor)


# noinspection PyShadowingNames
def binarize_as_array(im, threshold=None, t_factor=2.3):
    """Takes a PIL image in 'L' mode and changes each pixel value to O (black) or 255 (white) over the threshold
    :image: PIL image object :threshold: a value over which to binarize. If not specified, set automatically with
    specified skimage thresholding method or using the t_factor parameter value empirically determined by developer
    :returns a PIL image object in binary mode ('1')
    """
    array = np.asarray(im).copy()
    print(f' - thresholding method: {threshold}', end=', ')
    if not threshold:
        threshold = int((int(np.min(array)) + int(np.max(array))) / t_factor)  # calculating the base threshold
    elif threshold == 'min':
        threshold = threshold_minimum(array)
    elif threshold == 'otsu':
        threshold = threshold_otsu(array)
    print(f'threshold set to {threshold}')
    array = array > int(threshold)
    return Image.fromarray(array)  # .convert('1', dither=0)


def clean_edges_as_array(array, threshold):
    """Takes an array representation of an image and changes continuous areas from edges inwards where all pixels have
    luminosity below the threshold value to white.
    :returns: modified array"""
    for row in array:
        for i in range(len(row) - 1):  # left
            if row[i] < int(threshold * 1.5):
                row[i] = 255
            else:
                break
        for i in range(1, len(row) - 1):  # right
            i = -i
            if row[i] < int(threshold * 1.5):
                row[i] = 255
            else:
                break
    return array


def smart_binarize_as_array(im, threshold=None, t_factor=2.2, edges=False):
    """Takes a PIL image in 'L' mode and changes each pixel value to O (black) or 255 (white) over the dynamically
    adjusted row-specific threshold
    :image: PIL image object
    :threshold: a value over which to binarize. If not specified, set automatically to the midpoint
    between minimum and maximum luminosity values in the entire image, then dynamically adjusted for rows
    potentially containing pale text according to row-specific extremes
    :returns a PIL image object in binary mode ('1')
    """
    array = np.asarray(im).copy()
    floor = int(np.min(array))  # darkest point in the image
    ceiling = int(np.max(array))  # brightest point in the image
    print(f'luminosity range [{floor} : {ceiling}]')
    if threshold is None:
        threshold = int((floor + ceiling) / t_factor)  # calculating the base threshold
        print(f'threshold auto set to {threshold}')
    if edges:
        # Pre-cleaning the edges:
        print('Gnawing at the edges...')
        array = clean_edges_as_array(array, threshold)  # as is
        array = clean_edges_as_array(array.T, threshold).T  # and across
        print(f'new luminosity range: [{np.min(array)}:{np.max(array)}]')
        # Image.fromarray(array).show()
    # Binarizing:
    print('Binarizing content...')
    transposed = False
    if len(array) < len(array[0]):
        array = array.T
        print(' - transposed')
        transposed = True
    for row in array:
        bottom = int(row.min())
        top = int(row.max())
        if bottom > threshold * 1.5:  # entire row well above the threshold - no text, turn to white
            row[:] = 255
        elif bottom > (floor + (ceiling - floor) * .02):
            # might have some pale text - cautiously binarize over row-specific threshold
            row_threshold = (bottom + top) // t_factor
            # print(row_threshold, end=', ')
            for i in range(len(row) - 1):
                if row[i] > row_threshold:
                    row[i] = 255
                else:
                    row[i] = 0
        else:  # such rows are most likely to have normal black text - binarize over the base threshold
            for i in range(len(row) - 1):
                if row[i] > threshold:
                    row[i] = 255
                else:
                    row[i] = 0
    if transposed:
        print(' - transposing back...')
        array = array.T
    return Image.fromarray(array).convert('1', dither=0)


def count_white_rows(im):
    """Utility function used by deskew.
    Takes a binarized image, returns the number of pixel rows with zero black pixels"""
    array = np.asarray(im)
    count = 0
    for row in array:
        if np.mean(row) == 1:
            count += 1
    return count


def orientation(im):
    """Takes a binarized PIL image object and roughly checks that the text lines are more or less horizontal"""
    test_area = im.crop((int(im.width * 0.1), int(im.height * 0.1),
                         int(im.width * 0.9), int(im.height * 0.9)))
    white_original = count_white_rows(test_area) / test_area.height
    white_rotated = count_white_rows(test_area.rotate(270, expand=1)) / test_area.width
    if white_original > white_rotated:
        return 1
    if white_original < white_rotated:
        return 0
    return None


def clean_edges_row_nz(array):
    for row in array:
        if sum(row) == 0:
            row[:] = True
        else:
            row[:np.nonzero(row)[0][0]] = True
            row[np.nonzero(row)[0][-1]:] = True
    return array


def clean_edges(im):
    """Clears any continuous black areas at edges."""
    array = np.asarray(im).copy()  # converting the image to Numpy array
    # Getting rid of black at corners with transposition and back
    array = clean_edges_row_nz(clean_edges_row_nz(array).T).T
    return Image.fromarray(array)


def clip_edges(im):
    array = np.asarray(im).copy()  # converting the image to Numpy array



def clean_margins(im):
    """Takes a binarized PIL image object (mode '1'), identifies left and right content boundaries and clears all
    black pixels towards the edges. A scanning 'ray' of set width will start some reasonable distance into the image
    and scan towards each edge. As soon as it can shoot through from top to bottom detecting no or very few non-white
    pixels - this is considered content boundary. Any black pixels from this line towards the edge will be cleared.
    Upper and lower halves of vertical images are processed separately to deal with possible distortions.
    Returns image with clean margins """
    array = np.asarray(im).copy()  # converting the image to Numpy array
    ray_width = int(im.width * .02)  # setting scanning ray width to a fraction of the image width
    trigger = .995
    if ray_width < 3:
        ray_width = 3  # but no less than 3 pixels
    start = im.width // 4
    if im.width < im.height:  # vertical image processing in two halves
        slash = im.height // 2
        # Processing the upper half
        # Wiping the right margin clean
        for i in range(im.width - start, im.width - ray_width):
            if np.mean(array[:slash, i: (i + ray_width)]) > trigger:
                array[:slash, (i + ray_width):] = True
                break
        # Wiping the left margin clean
        for i in range(start):
            i = start - i
            if np.mean(array[:slash, i: (i + ray_width)]) > trigger:
                array[:slash, :i] = True
                break
        # Processing the lower half
        # Wiping the right margin clean
        for i in range(im.width - start, im.width - ray_width):
            if np.mean(array[slash:, i: (i + ray_width)]) > trigger:
                array[slash:, (i + ray_width):] = True
                break
        # Wiping the left margin clean
        for i in range(start):
            i = start - i
            if np.mean(array[slash:, i: (i + ray_width)]) > trigger:
                array[slash:, : i] = True
                break
    else:  # horizontal image, processing entire image in one go
        # Wiping the right margin clean
        for i in range(im.width - start, im.width - ray_width):
            if np.mean(array[:, i: (i + ray_width)]) > trigger:
                array[:, (i + ray_width):] = True
                break
        # Wiping the left margin clean
        for i in range(start):
            i = start - i
            if np.mean(array[:, i: (i + ray_width)]) > trigger:
                array[:, :i] = True
                break
    return Image.fromarray(array)


def deskew(im, echo=False):
    """Takes a (slightly) skewed image with text as PIL object in mode '1' and returns its straigthened copy"""
    angle = 0
    trial = im.crop((int(im.width * 0.1), int(im.height * 0.1),
                     int(im.width * 0.9), int(im.height * 0.9)))
    if max(trial.size) > 800:
        trial = small(trial, factor=(max(im.size) // 800)).convert('1', dither=0)
    print(f' - reduced to {trial.size}')
    # Trying positive tilt
    if count_white_rows(clean_edges(trial.rotate(1))) > count_white_rows(trial):
        trial = clean_edges(trial.rotate(1))
        angle += 1
        if echo:
            print(f' {angle}', end=' ')
        # and incrementing if helps
        while count_white_rows(clean_edges(trial.rotate(1))) > count_white_rows(trial):
            trial = clean_edges(trial.rotate(1))
            angle += 1
            if echo:
                print(f' {angle}', end=' ')
    # Trying negative tilt
    elif count_white_rows(clean_edges(trial.rotate(-1))) > count_white_rows(trial):
        trial = clean_edges(trial.rotate(-1))
        angle -= 1
        if echo:
            print(f' {angle}', end=' ')
        # and incrementing if helps
        while count_white_rows(clean_edges(trial.rotate(-1))) > count_white_rows(trial):
            trial = clean_edges(trial.rotate(-1))
            angle -= 1
            if echo:
                print(f' {angle}', end=' ')
    else:  # returning unchanged image
        if echo:
            print(' - no adjustment needed')
        return im
    print(f' - tilting by {angle} degrees')
    return clean_edges(im.rotate(angle))


def tesseract_osd(im):
    """Checks image orientation with tesseract and rotates it if necessary"""
    osd = pytesseract.image_to_osd(im).split('\n')
    print(f'Tesseract: {osd}', sep='\n')
    angle = int(osd[1].split(': ')[1])
    if angle != 0:
        print(f' - rotating {angle}')
        return im.rotate(angle, expand=1)
    return im


# Wrapper
def preprocess(image, threshold=None):
    """Takes an image with text, returns binarized straightened image with cleaned margins;
    uses a chain of functions defined above"""
    im = load_image(image)
    print('Loaded. Showing to Tesseract...')
    im = tesseract_osd(im)
    print('Binarizing...')
    im = binarize_as_array(im, threshold=threshold)
    print('Cleaning edges...')
    im = clean_edges(im)
    print('Deskewing...')
    im = deskew(im, echo=True)
    print('Cleaning margins...')
    im = clean_margins(im)
    return im

# TEXT RECOGNITION (WITH TESSERACT)

def segment(im,
            threshold=.0009,  # minimal proportion of black pixels in a row for it to qualify as a dark one
            gap=2,  # minimal gap between lines of text in pixels
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
    im.show()

    return boxes
# TODO: Rewrite the **segment** function using numpy array (and some other improvements)
# TODO: Teach it to avoid pictures but keep the sideways text lines


def recognize_by_lines(im, boxes):
    """Recognizes text from each box as a single line and returns a list of strings"""
    text_lines = []
    lang = input('Recognition language(s): ')
    if not lang:
        lang = 'tha'
    for box in boxes:
        line = pytesseract.image_to_string(im.crop(box), config='--psm 7', lang=lang)
        text_lines.append(line)

    return text_lines


class Image2Text:
    boxes = None
    lines = None
    text = None

    def __init__(self, image, pre=False, binarize=False):
        """Loads an image file to be recognized.
        :file: path to file or file object
        :pre: loads image with preprocessing if selected, default False
        :bin: loads image with binarization if selected, default False
        """
        if pre:
            print('Loading image file with full preprocessing')
            self.im = preprocess(image)
        elif binarize:
            print('Loading image file with binarization only')
            self.im = binarize_as_array(load_image(image))
        else:
            print('Loading image file with no preprocessing')
            self.im = load_image(image)
        self.path = image  # this is dubious!!! will only work with image passed as path, not file object

    def binarize(self):
        self.im = binarize_as_array(self.im)

    def recognize_as_is(self, lang=None):
        if not lang:
            lang = input('Recognition language(s): ')
        self.text = pytesseract.image_to_string(self.im, lang=lang)
        print('Recognition with no segmentation completed.')

    def recognize_by_lines(self):
        self.boxes = segment(self.im)
        self.lines = recognize_by_lines(self.im, self.boxes)  # merge with the next line?
        self.text = ''.join(self.lines)
        print('Recognition with segmentation completed.')

    def save_to_file(self):
        """Saving recognition results to text file named as the image file + txt extension into the same location
        where the original image was"""
        save_path = self.path + '.txt'
        with open(save_path, 'w', encoding='utf-8') as file:
            file.write(self.text)
        print(f'saved to {save_path}', end='\n\n')
