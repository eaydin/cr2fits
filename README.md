cr2fits
=======

cr2fits.py version **2.0.0**  
https://github.com/eaydin/cr2fits

A script to convert RAW images (Canon, Nikon etc.) to FITS images. It extracts only one color channel of the RAW image, and writes the necessary EXIF information to the FITS header.

# Dependencies

- Python 2.7 or => Python 3.2
- PyFITS or astropy: Older versions cr2fits (1.0.3 and earlier) depended on PyFITS. From 2.0.0 and on it added support for astropy. It uses astropy.io.fits which is basically the same as PyFITS for now. Favors PyFITS over astropy if you have both, since it is faster to load.
- dcraw: Try getting the latest version of this. Usually the ones in repositories is not the latest so it's possible that it'll convert your RAW images differently, corrupted. Get the latest version here : http://www.cybercom.net/~dcoffin/dcraw/ Also the one distributed with this package should work.

# Compiling dcraw:

Either use `gcc -o dcraw -O4 dcraw.c -lm -ljasper -ljpeg -llcms2` or `gcc -o dcraw -O4 dcraw.c -lm -DNODEPS` to compile it.  
You can then copy `dcraw` to your path (ex. `/usr/local/bin`). In order to copy to your path, you'll probably need root privileges.

# Usage

`cr2fits.py <cr2-filename> <color-index>`

- cr2-filename: This will obviously be the name of the file to convert.
- color-index: Can take three values, either 0, 1, 2 which represent Red, Green, Blue respectively.

# Output

The script will output the FITS file, added the color channel to the name of the output.

# Change log

## 2.0.0
- Added support for astropy
- Added support for usage as a module
- Use Numpy slicing instead of looping
- Direct dcraw output to BytesIO object, avoiding the I/O for the unused PPM file
- Updated license

# todo
- Add support for configparser
- Detect if output filename exists and give altenative name
- Output name detection fails with dot's (.) in the name, fix it
- Add support for 3D FITS files: an idea from the fork by [@mireianievas](https://github.com/mireianievas)
- Add support for multiple file inputs
