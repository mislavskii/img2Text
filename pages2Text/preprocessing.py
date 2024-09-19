import numpy as np
import pytesseract
from PIL import Image
from skimage.filters import threshold_minimum, threshold_otsu

# NOTATION NOTE -  as applied to variable/parameter names in the code below:
# 'image' refers to a general image file
# 'im' refers to a PIL image object


# noinspection PyShadowingNames


# IMAGE PREPROCESSING
# TODO: Clean the needless functions


def load_image(image, mode='L'):
    """Loads image from file, returns a PIL image object in 'L' mode (b/w)
    (output mode can be changed if necessary)"""
    im = Image.open(image).convert(mode)
    return im


def small(im, factor=12):
    """Takes a PIL image object, returns a copy reduced in size by :factor:"""
    return im.convert('L').reduce(factor)


def binarize_as_array(im, threshold=None, t_factor=.9):
    """Takes a PIL image in 'L' mode and changes each pixel value to O (black) or 255 (white) over the threshold
    :image: PIL image object :threshold: a value over which to binarize. If not specified, set automatically with
    specified skimage thresholding method or using the t_factor parameter value empirically determined by developer
    :returns a PIL image object in binary mode ('1')
    """
    array = np.asarray(im).copy()
    print(f' - thresholding method: {threshold}', end=', ')
    if not threshold:
        threshold = int((int(np.min(array)) + int(np.max(array))) / 2 * t_factor)  # calculating the base threshold
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
