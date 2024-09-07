#!/usr/bin/env python3
import os.path
import sys
import time
import argparse
from pypdf import PdfReader
from pypdf.filters import BytesIO

'''
Extract images from a pdf file, possibly accounting for softmask and 
compositing onto a background color
'''

parser = argparse.ArgumentParser(description='Extract images from a pdf')
# positional
parser.add_argument('file', type=str, help='pdf filename', default=None)
# optional
parser.add_argument('--pages', '-p', type=int, nargs='+', default=None, required=False, help='page number(s)')
parser.add_argument('--page-range', '-r', type=int, nargs=2, default=None, required=False, help='page range', metavar=('PAGE', 'PAGE'))
parser.add_argument('--image', '-i', type=str, default=None, required=False, help='image name to extract (default all images)')
parser.add_argument('--list', action='store_true', help='print list of images on the page instead of extracting images')

# This lets us use + for nargs on --pages and --bg above
if len(sys.argv) > 1 and os.path.exists(sys.argv[-1]):
    args = parser.parse_args(sys.argv[0:-1])
    args.file = sys.argv[-1]
else:
    args = parser.parse_args()


def get_filename(page: int, node_name: str):
    return 'Page_' + str(page) + '_' + node_name


def image_list_from_page(pdf_reader: PdfReader, page_number: int):
    image_list = []
    page = pdf_reader.pages[page_number - 1]

    for img in page.images:
        image_list += [get_filename(page_number, img.name)]
    return image_list


def extract_from_page(pdf_reader: PdfReader, page_number: int, image_name: str):
    page = pdf_reader.pages[page_number - 1]

    for img in page.images:
        if image_name is not None and img.name != image_name:
            continue

        filename = get_filename(page_number, img.name)
        data_bytes = img.data
        # pypdf outputs jp2 when the data format is jpeg but a mask is
        # present. convert and output png instead
        if filename.endswith('.jp2'):
            filename = filename.replace('.jp2', '.png')
            bytes_io = BytesIO()
            img.image.save(bytes_io, 'PNG')
            data_bytes = bytes_io.getvalue()
        with open(filename, 'wb') as out_file:
            out_file.write(data_bytes)
    return


def progressbar(iter, total, prefix="", size=60, start_time=None, out=sys.stdout):
    iter += 1
    frac = iter / total
    pip_num = int(size * frac)
    # time estimate calculation and string
    progress_str = f"{prefix}[{u'█' * pip_num}{('.' * (size - pip_num))}] {iter}/{total}"
    if start_time is not None:
        remaining = ((time.time() - start_time) / frac) * (1 - frac)
        mins, sec = divmod(remaining, 60)  # limited to minutes
        progress_str += " Est. "
        if mins > 0:
            progress_str += f"{int(mins):02}m"
        else:
            progress_str += f"{int(sec):02}s"

    print(progress_str, end='\r', file=out, flush=True)
    if iter >= total:
        print("\n", flush=True, file=out)


if __name__ == '__main__':
    pdf_reader = PdfReader(args.file)

    if args.pages is not None:
        pages = list(args.pages)
    elif args.page_range is not None:
        pages = list(range(args.page_range[0], args.page_range[1] + 1))
    else:
        pages = list(range(1, len(pdf_reader.pages) + 1))

    image_list = []
    start_time = time.time()
    for step, page_number in enumerate(pages):
        if args.list:
            image_list += image_list_from_page(pdf_reader, page_number)
        else:
            extract_from_page(pdf_reader, page_number, args.image)
            progressbar(step, len(pages), " Page Progress ", 50, start_time)

    if len(image_list) > 0:
        print(image_list)
        print(str(len(image_list)) + ' items on ' + str(len(pages)) + ' pages')
