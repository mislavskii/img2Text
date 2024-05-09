import os
import threading

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from datetime import datetime as dt

from sipSongPanNa.img2text import Preprocessor

im_dir = 'sipSongPanNa/pages/clipped_RGB/'


def batch_find_blocks(dir_entries, dst_dir):
    for entry in dir_entries:
        name = entry.name
        if name.endswith('.png'):
            pp = Preprocessor(Image.open(entry.path))
            pp.find_all_blocks()
            # print(f'{name}: ', pp.blocks)
            out_im = pp.draw_blocks()
            out_im.save(
                dst_dir + name.replace(
                    '.png', f'_blocks_{pp.block_boxes["params"]["psm"]}_{pp.block_boxes["params"]["mode"]}.png'))


def batch_process_concurrent(function, collection, other_args):
    if len(collection) < 2:
        print('There is no batch. No need for concurrent processing')
        return
    n_chunks = max(os.cpu_count() // 2, 2)
    n_chunks = min(len(collection), n_chunks)
    collection = np.array(collection)
    chunks = np.array_split(collection, n_chunks)
    print(len(chunks))
    threads = [threading.Thread(
        target=function, args=(chunk, *other_args), name=f'{chunk[0]}...{chunk[-1]}') for chunk in chunks]
    start = dt.now()
    print(f'Starting {len(threads)} threads: {start}')
    for thread in threads:
        print(thread)
        thread.start()
    for thread in threads:
        thread.join()
        print(thread)
    print(f'Done in {dt.now() - start}')


def main() -> None:
    batch_process_concurrent(batch_find_blocks,
                             [entry for entry in os.scandir(im_dir) if entry.name.endswith('.png')],
                             (im_dir + 'blocks/',)
                             )


if __name__ == '__main__':
    main()
