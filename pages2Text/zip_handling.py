import os
import zipfile

from PIL import Image


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
