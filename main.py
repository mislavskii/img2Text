import matplotlib.pyplot as plt

from sipSongPanNa import img2text as it
from screen2Text import screen2text as st
im_dir = 'sipSongPanNa/pages/clipped_RGB/'


def main() -> None:
    im = it.Image.open(im_dir + 'page_043.png')
    pp = it.Preprocessor(im)
    pp.find_all_blocks(mode='RGB')
    plt.imshow(pp.draw_blocks())
    pp.show_block_variants()


if __name__ == '__main__':
    main()
