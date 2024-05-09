"""
rewriting the Image2Text class for greater flexibility
"""

import os
from PIL import Image, ImageDraw, ImageOps
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from skimage.filters import *
import pytesseract

tess_path = 'C:/Program Files/Tesseract-OCR/tesseract.exe'
# tess_path = r'C:\Users\User\AppData\Local\Tesseract-OCR\tesseract.exe'
pytesseract.pytesseract.tesseract_cmd = tess_path
TESSDATA_PREFIX = r'C:/Program Files/Tesseract-OCR/tessdata'


# TESSDATA_PREFIX = 'C:/Users/User/AppData/Local/Tesseract-OCR/tessdata'

# NOTATION NOTE -  as applied to variable/parameter names in the code below:
# 'image' refers to a general image file
# 'im' refers to a PIL image object


# noinspection PyShadowingNames

# TODO: rewritten without zip. TEST!
def thumbsheet(images,
               sheet_width=900,
               resize_factor=20,
               margin=3
               ):
    """
    Builds a thumbsheet of all images from a collection :param images: of PIL image objects
    :type margin: int
    :param sheet_width: desired width of the thumbsheet in pixels
    :param resize_factor: divides original image size by this value to get thumbnail size
    :param margin: margin at thumbsheet edges in pixels
    :return: thumbsheet as a PIL.Image object
    """
    # Calculating the thumbsheet height
    sheet_height = margin
    row_height = margin
    row_length = margin
    for im in images:
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
    for im in images:
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


# IMAGE PREPROCESSING
# TODO: Clean the needless functions in this section

def load_image(image, mode='L'):
    """Loads image from file, returns a PIL image object in 'L' mode (b/w)
    (output mode can be changed if necessary)"""
    im = Image.open(image)
    if mode:
        im = im.convert(mode)
    return im


def small(im, factor=12):
    """Takes a PIL image object, returns a copy grayscale reduced in size by :factor:"""
    return im.convert('L').reduce(factor)


# noinspection PyShadowingNames
def binarize_as_array(im, threshold=None, skew=1, echo=False):
    """Takes a PIL image and changes each pixel value to False (black) or True (white) over the :threshold:
    :image: PIL image object
    :threshold: a value over which to binarize. If not specified, set automatically with
    specified skimage thresholding method or as the middle value between min and max for entire image
    adjusted by :skew: if needed
    :returns: a PIL image object in binary mode ('1')
    """
    array = np.asarray(im if im.mode == 'L' else im.convert('L')).copy()
    if echo:
        print(f' - thresholding method: {threshold}', end=', ')
    if not threshold:
        threshold = int((np.min(array) + np.max(array)) / 2 * skew)  # calculating the base threshold
    elif threshold == 'min':
        threshold = threshold_minimum(array)
    elif threshold == 'otsu':
        threshold = threshold_otsu(array)
    if echo:
        print(f'threshold set to {threshold}')
    array = array > threshold
    # array[array >= threshold] = 255
    # array[array < threshold] = 0
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


def clip_sides_2d(im):
    """Clips continuous black edges sideways on a grayscale image represented as a 2d array"""
    array = np.asarray(im).copy()  # converting the image to Numpy array
    array = array.T
    i = 0
    while not array[i].sum():  # black row
        i += 1
    top = i
    while i < array.shape[0] and array[i].sum():  # non-black row
        i += 1
    bottom = i if i > top else array.shape[0] - 1
    array = array[top:bottom]
    return Image.fromarray(array.T)


def clip_sides_3d(im):
    """Clips continuous black edges sideways on an RGB image represented as a 3d array"""
    array = np.asarray(im).copy()  # converting the image to Numpy array
    i = 0
    while not array[:, i, :].sum():  # black column, 3 colors deep
        i += 1
    left = i
    while i < array.shape[1] and array[:, i, :].sum():  # non-black column
        i += 1
    right = i if i > left else array.shape[1] - 1
    array = array[:, left:right, :]
    return Image.fromarray(array)


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
    """Takes a (slightly) skewed image with text as PIL Image object and returns its straightened copy"""
    angle = 0
    trial = im.crop((int(im.width * 0.1), int(im.height * 0.1),
                     int(im.width * 0.9), int(im.height * 0.9)))
    if trial.mode != '1':
        trial = binarize_as_array(trial)
        trial.save('pages/tmp/' + 'trial.png')
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


class Preprocessor:

    def __init__(self, pil_image):
        self.im = pil_image
        self.data = pd.DataFrame()
        self.block_boxes = {}

    def get_image_data(self, lang='tha', psm=3, mode='RGB', thresh=None):
        im = self.im.copy()
        self.block_boxes['params'] = dict(lang=lang, psm=psm, mode=mode, thresh=thresh)
        if mode == 'L':
            im = im.convert('L')
        if mode == '1':
            im = binarize_as_array(im, thresh)
        self.data = pd.DataFrame(pytesseract.image_to_data(im,
                                                           lang=lang, config=f'--psm {psm}',
                                                           output_type='data.frame'))

    def find_all_blocks(self, lang='tha', psm=3, mode='RGB', thresh=None):
        self.block_boxes.clear()
        self.block_boxes['boxes'] = {}
        self.get_image_data(lang, psm, mode, thresh)
        data = self.data
        blocks = data[data.text.isna() & (data.level == 2)]
        boxes = self.block_boxes['boxes']
        for i, row in blocks.iterrows():
            boxes[row.block_num] = row.left, row.top, row.left + row.width, row.top + row.height

    def draw_blocks(self, width=1, color='blue') -> Image:
        """
        :param width: block outline width in px
        :param color: block outline color
        :return: PIL image showing discovered text blocks as defined in `block-boxes`
        drawn onto original image
        """
        boxed = self.im.copy()
        boxes = self.block_boxes['boxes']
        for box in boxes.values():
            draw = ImageDraw.Draw(boxed)
            draw.rectangle(box, width=width, outline=color)
        return boxed

    def build_sampling_sheet(self, line_width=2, color='navy', figsize=(9, 13)):
        """builds 3x3 grid of block discovery results overlain on original image
        for the three psm values and three image modes"""
        fig, axs = plt.subplots(3, 3, figsize=figsize, facecolor='whitesmoke',
                                layout='tight', sharex='col', sharey='row')
        fig.suptitle('The effect of psm value and image mode on text block discovery by Tesseract\n')

        modes = np.array((None, 'L', '1') * 3).reshape(3, 3).T
        psms = np.array((1, 3, 6) * 3).reshape(3, 3)
        for ax, mode, psm in zip(axs.flatten(), modes.flatten(), psms.flatten()):
            ax.spines.top.set_visible(False)
            ax.spines.left.set_visible(False)
            ax.spines.right.set_visible(False)
            ax.spines.bottom.set_visible(False)
            ax.tick_params(labelsize='x-small')
            self.find_all_blocks(mode=mode, psm=psm)
            ax.imshow(self.draw_blocks(width=line_width, color=color))
            if mode is None:
                ax.set_title(f'psm {psm}')
                if psm == 1:
                    ax.set_ylabel('RGB')
            if mode == 'L' and psm == 1:
                ax.set_ylabel('Grayscale')
            if mode == '1':
                ax.set_xlabel(f'psm {psm}')
                if psm == 1:
                    ax.set_ylabel('Binary')

        plt.savefig('pages/tmp/sampling_sheet.png')
        plt.show()


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


print('>> img2text imported.')
