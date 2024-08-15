#!/usr/bin/env python3
import PyPDF2
import argparse
from PIL import Image

'''
Extract images from a pdf file, possibly accounting for softmask and compositing onto a background color
'''

parser = argparse.ArgumentParser(description='Extract images from a pdf')
# positional
parser.add_argument('file', type=str, help='pdf filename')
# optional
parser.add_argument('--page', '-p', type=int, default=None, required=False, help='page number, or omit')
parser.add_argument('--image', '-i', type=str, default=None, required=False, help='image name to extract, or "all" to extract all (default)')
parser.add_argument('--bg', '-b', type=int, nargs='+', default=[0, 0, 0, 0], required=False, help='background color if a mask is present. 0=black 255=white, or 3/4 integer R G B (A)')
parser.add_argument('--debug', action='store_true', help='print pdf node debug information and show intermediate images')
parser.add_argument('--list', action='store_true', help='print list of images on the page instead of extracting images')
parser.add_argument('--interactive', action='store_true', help='Run interactively, prompting whether to save each image on the page')

args = parser.parse_args()


def get_filename(page, node_name, extension):
    return 'Page_' + str(page) + '_' + node_name + extension


def image_list_from_page(pdf_reader, page_number):
    image_list = []
    page = pdf_reader.pages[page_number - 1]
    x_object = page['/Resources']['/XObject'].get_object()
    list_mode = args.list

    for obj in x_object:
        if x_object[obj]['/Subtype'] == '/Image':
            if list_mode:
                image_list += [get_filename(page_number, obj[1:], '')]
    return image_list


def extract_from_page(pdf_reader, page_number, image_name, bg):
    page = pdf_reader.pages[page_number - 1]
    x_object = page['/Resources']['/XObject'].get_object()

    for obj in x_object:
        if x_object[obj]['/Subtype'] == '/Image':
            if image_name is not None and obj[1:] != image_name:
                continue

            image_node = x_object[obj]
            colorspace = image_node['/ColorSpace']
            # for icc color profiles use whatever the 'alternate' is set to
            # rather than trying to decode icc
            if '/ICCBased' in colorspace:
                colorspace = colorspace[1].get_object()
                if '/Alternate' in colorspace:
                    colorspace = colorspace['/Alternate']
                else:
                    colorspace = '/DeviceRGB'  # uhh idfk

            if args.debug:
                print('-'*80)
                print('Node: {}'.format(image_node))
                print('ColorSpace: {}'.format(colorspace))
                if '/Metadata' in image_node:
                    print('Metadata:')
                    print('>'*80)
                    print(image_node['/Metadata'].get_data().decode())
                    print('<'*80)

            size = (image_node['/Width'], image_node['/Height'])

            mask = None
            if '/SMask' in image_node:
                mask_node = image_node['/SMask']
                if args.debug:
                    print('MaskNode: {}'.format(mask_node))
                    print('MaskColorSpace: {}'.format(mask_node["/ColorSpace"]))
                if mask_node['/ColorSpace'] == '/DeviceGray':
                    mask_color = 'L'
                else:
                    mask_color = None

                if args.debug and '/Metadata' in mask_node:
                    print('MaskMetadata:')
                    print('>'*80)
                    print(mask_node['/Metadata'].get_data().decode())
                    print('<'*80)

                # the additional arguments for specific decoders (jpeg etc) are poorly documented. Best
                # bet is find the relevant method in the PIL decode.c and look for the PyArg_ParseTuple call
                # https://github.com/python-pillow/Pillow/blob/main/src/decode.c
                if mask_color is not None and mask_node['/Filter'] == '/FlateDecode':
                    data = mask_node.get_data()
                    # the fuck?
                    if isinstance(data, str):
                        data = bytes(data, 'utf_8')
                    mask = Image.frombytes(mask_color, size, data)
                elif mask_color is not None and mask_node['/Filter'] == '/DCTDecode':
                    mask = Image.frombytes(mask_color, size, mask_node.get_data(), 'jpeg', mask_color, mask_color)
                elif mask_color is not None and mask_node['/Filter'] == '/JPXDecode':
                    mask = Image.frombytes(mask_color, size, mask_node.get_data(), 'jpeg2k', mask_color, mask_color)

            # Here are the fucking image modes, again poorly documented
            # https://github.com/python-pillow/Pillow/blob/main/src/libImaging/Unpack.c
            if colorspace == '/DeviceRGB':
                img_color = 'RGB'
            elif colorspace == '/DeviceCMYK':
                img_color = 'CMYK'
            elif '/Indexed' in colorspace:
                # png, palettized
                img_color = 'P'
            else:
                img_color = 'RGB'  # uhhh sure

            img = None
            filename = ''

            # see note above about frombytes additional args
            if image_node['/Filter'] == '/FlateDecode':
                data = image_node.get_data()
                # the fuck?
                if isinstance(data, str):
                    data = bytes(data, 'utf_8')
                img = Image.frombytes(img_color, size, data)
                filename = get_filename(page_number, obj[1:], '.png')
            elif image_node['/Filter'] == '/DCTDecode':
                # how the fuck am i supposed to know these are inverted? idfk but they are
                img = Image.frombytes(img_color, size, image_node.get_data(), 'jpeg', img_color, img_color + ';I')
                filename = get_filename(page_number, obj[1:], '.jpg')
            elif image_node['/Filter'] == '/JPXDecode':
                img = Image.frombytes(img_color, size, image_node.get_data(), 'jpeg2k', img_color, img_color + ';I')
                filename = get_filename(page_number, obj[1:], '.jp2')

            if args.debug and mask is not None:
                img.show('{} color'.format(filename))

            if img is not None and mask is not None:
                if args.debug:
                    mask.show('{} mask'.format(filename))
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                img.putalpha(mask)
                solid_color = Image.new('RGBA', size, bg)
                try:
                    solid_color.alpha_composite(img)
                except:
                    print('Failed for image {}'.format(obj))
                    print('Image {}'.format(img))
                    print('Solid {}'.format(solid_color))
                if bg[3] == 255:
                    img = solid_color.convert('RGB')
                else:
                    filename = get_filename(page_number, obj[1:], '.png')  # only png output supported if the background has non-1 alpha

            if args.interactive:
                img.show(title=filename)
                if input('Save image {}? y/n '.format(filename)).lower() != 'y':
                    img = None

            if img is not None:
                img.save(filename)
    return


if __name__ == '__main__':
    if len(args.bg) == 1:
        bg = (args.bg[0], args.bg[0], args.bg[0], 255)
    elif len(args.bg) == 3:
        bg = tuple(args.bg) + (255,)
    elif len(args.bg) == 4:
        bg = tuple(args.bg)
    else:
        bg = (0, 0, 0, 0)

    pdf_file = open(args.file, 'rb')
    pdf_reader = PyPDF2.PdfFileReader(pdf_file)

    if args.page is None:
        pages = list(range(1, len(pdf_reader.pages)+1))
    else:
        pages = [args.page]

    image_list = []
    for page_number in pages:
        if args.list:
            image_list += image_list_from_page(pdf_reader, page_number)

        else:
            extract_from_page(pdf_reader, page_number, args.image, bg)
    pdf_file.close()

    if len(image_list) > 0:
        print(image_list)
        print(str(len(image_list)) + ' items on ' + str(len(pages)) + ' pages')
