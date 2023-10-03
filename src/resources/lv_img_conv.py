#!/usr/bin/env python3
import argparse
import pathlib
import sys
import decimal
from PIL import Image


def classify_pixel(value, bits):
    def round_half_up(v):
        """python3 implements "propper" "banker's rounding" by rounding to the nearest
        even number. Javascript rounds to the nearest integer.
        To have the same output as the original JavaScript implementation add a custom
        rounding function, which does "school" rounding (to the nearest integer).

        see: https://stackoverflow.com/questions/43851273/how-to-round-float-0-5-up-to-1-0-while-still-rounding-0-45-to-0-0-as-the-usual
        """
        return int(decimal.Decimal(v).quantize(decimal.Decimal('1'), rounding=decimal.ROUND_HALF_UP))
    tmp = 1 << (8 - bits)
    val = round_half_up(value / tmp) * tmp
    if val < 0:
        val = 0
    return val


def test_classify_pixel():
    # test difference between round() and round_half_up()
    assert classify_pixel(18, 5) == 16
    # school rounding 4.5 to 5, but banker's rounding 4.5 to 4
    assert classify_pixel(18, 6) == 20


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("img",
        help="Path to image to convert to C header file")
    parser.add_argument("-o", "--output-file",
        help="output file path (for single-image conversion)",
        required=True)
    parser.add_argument("-f", "--force",
        help="allow overwriting the output file",
        action="store_true")
    # --image-name, -i     name of image structure
    parser.add_argument("-c", "--color-format",
        help="color format of image",
        default="CF_TRUE_COLOR_ALPHA",
        choices=[
            "CF_ALPHA_1_BIT", "CF_ALPHA_2_BIT", "CF_ALPHA_4_BIT",
            "CF_ALPHA_8_BIT", "CF_INDEXED_1_BIT", "CF_INDEXED_2_BIT", "CF_INDEXED_4_BIT",
            "CF_INDEXED_8_BIT", "CF_RAW", "CF_RAW_CHROMA", "CF_RAW_ALPHA",
            "CF_TRUE_COLOR", "CF_TRUE_COLOR_ALPHA", "CF_TRUE_COLOR_CHROMA", "CF_RGB565A8",
        ],
        required=True)
    parser.add_argument("-t", "--output-format",
        help="output format of image",
        default="bin", # default in original is 'c'
        choices=["c", "bin"])
    parser.add_argument("--binary-format",
        help="binary color format (needed if output-format is binary)",
        default="ARGB8565_RBSWAP",
        choices=["ARGB8332", "ARGB8565", "ARGB8565_RBSWAP", "ARGB8888"])
    #  --swap-endian, -s    swap endian of image                            [boolean]
    #  --dither, -d         enable dither                                   [boolean]
    args = parser.parse_args()

    img_path = pathlib.Path(args.img)
    out = pathlib.Path(args.output_file)
    if not img_path.is_file():
        print(f"Input file is missing: '{args.img}'")
        return 1
    print(f"Beginning conversion of {args.img}")
    if out.exists():
        if args.force:
            print(f"overwriting {args.output_file}")
        else:
            print(f"output-file exists, set --force to allow overwriting of file")
            return 0
    out.touch()

    # only implemented the bare minimum, everything else is not implemented
    if args.color_format not in ["CF_INDEXED_1_BIT", "CF_TRUE_COLOR_ALPHA"]:
        raise NotImplementedError(f"args.color_format '{args.color_format}' not implemented")
    if args.output_format != "bin":
        raise NotImplementedError(f"args.output_format '{args.output_format}' not implemented")
    if args.binary_format not in ["ARGB8565_RBSWAP", "ARGB8888"]:
        raise NotImplementedError(f"args.binary_format '{args.binary_format}' not implemented")

    # open image using Pillow
    img = Image.open(img_path)
    img_height = img.height
    img_width = img.width
    print(f"loaded image with width x heigth: {img_width} x {img_height}")
    if args.color_format == "CF_TRUE_COLOR_ALPHA" and args.binary_format == "ARGB8888":
        buf = bytearray(img_height*img_width*4) # 4 bytes (32 bit) per pixel
        for y in range(img_height):
            for x in range(img_width):
                i = (y*img_width + x)*4 # buffer-index
                pixel = img.getpixel((x,y))
                r = pixel[0]
                g = pixel[1]
                b = pixel[2]
                a = pixel[3]
                buf[i + 0] = r
                buf[i + 1] = g
                buf[i + 2] = b
                buf[i + 3] = a

    elif args.color_format == "CF_TRUE_COLOR_ALPHA" and args.binary_format == "ARGB8565_RBSWAP":
        buf = bytearray(img_height*img_width*3) # 3 bytes (24 bit) per pixel
        for y in range(img_height):
            for x in range(img_width):
                i = (y*img_width + x)*3 # buffer-index
                pixel = img.getpixel((x,y))
                r_act = classify_pixel(pixel[0], 5)
                g_act = classify_pixel(pixel[1], 6)
                b_act = classify_pixel(pixel[2], 5)
                a = pixel[3]
                if r_act > 0xF8:
                    r_act = 0xF8
                if g_act > 0xFC:
                    g_act = 0xFC
                if b_act > 0xF8:
                    b_act = 0xF8
                c16 = ((r_act) << 8) | ((g_act) << 3) | ((b_act) >> 3) # RGR565
                buf[i + 0] = (c16 >> 8) & 0xFF
                buf[i + 1] = c16 & 0xFF
                buf[i + 2] = a
                #buf_i0 = buf[i + 0]
                #buf_i1 = buf[i + 1]
                #buf_i2 = buf[i + 2]
                #print(f"{x},{y}: {buf_i0:02x}, {buf_i1:02x}, {buf_i2:02x}")
                #if (x == 8 and y == 2):
                #if (x == 10 and y == 0):
                #    tmp_5 = 1 << (8 - 5)
                #    tmp_6 = 1 << (8 - 6)
                #    r = pixel[0]
                #    g = pixel[1]
                #    b = pixel[2]
                #    val_r = round(r / tmp_5) * tmp_5
                #    val_g = round(g / tmp_6) * tmp_6
                #    val_b = round(b / tmp_5) * tmp_5
                #    print("rgba:", r, g, b, a)
                #    print("rgba_act:", r_act, g_act, b_act, a)
                #    print("classify_pixel(r, 5):", "tmp:", tmp_5, "r/tmp:", r/tmp_5, "round(r/tmp):", round(r/tmp_5), "val:", val_r)
                #    print("classify_pixel(g, 6):", "tmp:", tmp_6, "g/tmp:", g/tmp_6, "round(g/tmp):", round(g/tmp_6), "val:", val_g)
                #    print("classify_pixel(b, 5):", "tmp:", tmp_5, "b/tmp:", b/tmp_5, "round(b/tmp):", round(b/tmp_5), "val:", val_b)
                #    print("c16:", c16)
                #    print(f"{x},{y}: {buf_i0:02x}, {buf_i1:02x}, {buf_i2:02x}")
                #    print("found it!")
            print(f"done line {y}")

    elif args.color_format == "CF_INDEXED_1_BIT": # ignore binary format, use color format as binary format
        w = img_width >> 3
        if img_width & 0x07:
            w+=1
        max_p = w * (img_height-1) + ((img_width-1) >> 3) + 8  # +8 for the palette
        buf = bytearray(max_p+1)

        for y in range(img_height):
            for x in range(img_width):
                c, a = img.getpixel((x,y))
                p = w * y + (x >> 3) + 8  # +8 for the palette
                #if(!isset(this.d_out[p])) this.d_out[p] = 0  # Clear the bits first
                buf[p] |= (c & 0x1) << (7 - (x & 0x7))
        # write palette information
        palette_size = 2
        bits_per_value = 1
        # write 8 palette bytes
        buf[0] = 0
        buf[1] = 0
        buf[2] = 0
        buf[3] = 0
        # Normally there is much math behind this, but for the current use case this is close enough
        buf[4] = 255
        buf[5] = 255
        buf[6] = 255
        buf[7] = 255
    else:
        # raise just to be sure
        raise NotImplementedError(f"args.color_format '{args.color_format}' with args.binary_format '{args.binary_format}' not implemented")

    # write header
    match args.color_format:
        case "CF_TRUE_COLOR_ALPHA":
            lv_cf = 5
        case "CF_INDEXED_1_BIT":
            lv_cf = 7
        case _:
            # raise just to be sure
            raise NotImplementedError(f"args.color_format '{args.color_format}' not implemented")
    header_32bit = lv_cf | (img_width << 10) | (img_height << 21)
    buf_out = bytearray(4 + len(buf))
    buf_out[0] = header_32bit & 0xFF
    buf_out[1] = (header_32bit & 0xFF00) >> 8
    buf_out[2] = (header_32bit & 0xFF0000) >> 16
    buf_out[3] = (header_32bit & 0xFF000000) >> 24
    buf_out[4:] = buf

    # write byte buffer to file
    with open(out, "wb") as f:
        f.write(buf_out)
    return 0


if __name__ == '__main__':
    if "--test" in sys.argv:
        # run small set of tests and exit
        print("running tests")
        test_classify_pixel()
        print("success!")
        sys.exit(0)
    # run normal program
    sys.exit(main())
