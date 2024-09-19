from PIL import Image
import numpy as np


def clean_margins(im):
    """Takes a binarized PIL image object (mode '1'), identifies left and right content boundaries
    and clears all black pixels towards the edges by finding the vertical content boundaries and
    wiping any black artifacts off the margins. A scanning 'ray' of set width will start in the center
    and scan towards each edge. As soon as it can shoot through from top to bottom detecting no non-white
    pixels - this is considered content boundary. Any black pixels from this line towards the edge will be cleared.
    Upper and lower halves of the image are processed separately to deal with possibly slanted perspective.
    Returns cleaner image"""
    array = np.asarray(im).copy()  # converting the image to Numpy array
    ray_width = int(im.width * .005)  # setting scanning ray width to a fraction of the image width
    if ray_width < 3:
        ray_width = 3  # but no less than 3 pixels
    start = im.width // 3
    slash = im.height // 2
    # Processing the upper half
    # Wiping the right margin clean
    for i in range(im.width - start, im.width - ray_width):
        if np.mean(array[:slash, i: (i + ray_width)]) > .99:
            array[:slash, (i + ray_width):] = True
            break
    # Wiping the left margin clean
    for i in range(ray_width, start):
        i = start - i
        if np.mean(array[:slash, i: (i + ray_width)]) > .99:
            array[:slash, : (i - ray_width)] = True
            break
    # Processing the lower half
    # Wiping the right margin clean
    for i in range(im.width - start, im.width - ray_width):
        if np.mean(array[slash:, i: (i + ray_width)]) > .99:
            array[slash:, (i + ray_width):] = True
            break
    # Wiping the left margin clean
    for i in range(ray_width, start):
        i = start - i
        if np.mean(array[slash:, i: (i + ray_width)]) > .99:
            array[slash:, : (i - ray_width)] = True
            break
    return Image.fromarray(array)


im = Image.open('resources/IMG_5265.jpg').convert('1', dither=0)

im = clean_margins(im)

im.show()
