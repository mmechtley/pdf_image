#!/usr/bin/env python3
import PyPDF2
import argparse
from PIL import Image

'''
Extract images from a pdf file, possibly accounting for softmask and compositing onto a background color
'''

parser = argparse.ArgumentParser(description='Extract images from a pdf')
parser.add_argument('page', type=int, help='page number')
parser.add_argument('-image', type=str, default='all', required=False, help='image name to extract, or "all" to extract all (default)')
parser.add_argument('-bg', type=int, nargs='+', default=[255], required=False, help='background color if a mask is present. 0=black 255=white, or 3/4 integer R G B (A)')
parser.add_argument('file', type=str, help='pdf filename')
parser.add_argument('--debug', action='store_true', help='print pdf node debug information')
parser.add_argument('--list', action='store_true', help='print list of images on the page instead of extracting images')

args = parser.parse_args()

pdf_file = open(args.file, 'rb')

pdf_reader = PyPDF2.PdfFileReader(pdf_file)

page = pdf_reader.pages[args.page - 1]
x_object = page["/Resources"]["/XObject"].get_object()
images = []
list_mode = args.list
if len(args.bg) == 1:
    bg = (args.bg[0], args.bg[0], args.bg[0], 255)
elif len(args.bg) == 3:
    bg = tuple(args.bg) + (255, )
elif len(args.bg) == 4:
    bg = tuple(args.bg)
else:
    bg = (255, 255, 255, 255)

for obj in x_object:
    if x_object[obj]["/Subtype"] == "/Image":
        if list_mode:
            images += [obj[1:]]
            continue
        elif args.image != 'all' and obj[1:] != args.image:
            continue

        size = (x_object[obj]["/Width"], x_object[obj]["/Height"])
        data = x_object[obj].get_data()
        if args.debug:
            print(f'Node: {x_object[obj]}')

        mask = None
        if "/SMask" in x_object[obj]:
            maskNode = x_object[obj]["/SMask"]
            if args.debug:
                print(f'  MaskNode: {maskNode}')
                print(f'  MaskColorSpace: {maskNode["/ColorSpace"]}')
            if maskNode['/ColorSpace'] == "/DeviceGray":
                mask_color = "L"
            else:
                mask_color = None
            if mask_color is not None and maskNode['/Filter'] == "/FlateDecode":
                mask = Image.frombytes(mask_color, size, maskNode.get_data())
            elif mask_color is not None and maskNode['/Filter'] == "/DCTDecode":
                mask = Image.frombytes(mask_color, size, maskNode.get_data(), "jpeg", mask_color, mask_color)
            elif mask_color is not None and maskNode['/Filter'] == '/JPXDecode':
                mask = Image.frombytes(mask_color, size, maskNode.get_data(), "jpeg2k", mask_color, mask_color)

        colorspace = x_object[obj]["/ColorSpace"]
        # for icc color profiles use whatever the "alternate" is set to
        # rather than trying to decode icc
        if "/ICCBased" in colorspace:
            colorspace = colorspace[1].get_object()
            if "/Alternate" in colorspace:
                colorspace = colorspace["/Alternate"]
            else:
                colorspace = "/DeviceRGB"  # uhh idfk
        if args.debug:
            print(f'ColorSpace: {colorspace}')

        # Here are the fucking image modes:
        # https://github.com/python-pillow/Pillow/blob/main/src/libImaging/Unpack.c
        if colorspace == "/DeviceRGB":
            img_color = "RGB"
        elif '/Indexed' in colorspace:
            # png, palettized
            img_color = "P"
        else:
            img_color = "RGB"  # uhhh sure

        img = None
        filename = ""
        if x_object[obj]["/Filter"] == "/FlateDecode":
            img = Image.frombytes(img_color, size, data)
            filename = obj[1:] + ".png"
        elif x_object[obj]["/Filter"] == "/DCTDecode":
            # how the fuck am i supposed to know these are inverted? idfk
            img = Image.frombytes(img_color, size, data, "jpeg", img_color, img_color + ";I")
            filename = obj[1:] + ".jpg"
        elif x_object[obj]["/Filter"] == "/JPXDecode":
            img = Image.frombytes(img_color, size, data, "jpeg2k", img_color, img_color + ";I")
            filename = obj[1:] + ".jp2"

        if args.debug:
            img.show()

        if img is not None and mask is not None:
            if args.debug:
                mask.show()
            if img.mode != "RGB":
                img = img.convert("RGB")
            img.putalpha(mask)
            solid_color = Image.new("RGBA", size, bg)
            try:
                solid_color.alpha_composite(img)
            except:
                print(f'Failed for image {obj}')
                print(f'Image {img}')
                print(f'Solid {solid_color}')
            if bg[3] == 255:
                img = solid_color.convert("RGB")
            else:
                filename = obj[1:] + ".png"  # only png if the background has non-1 alpha

        if img is not None:
            img.save(filename)

pdf_file.close()

if len(images) > 0:
 print(images)