cr2fits
=======

cr2fits.py version **2.0.0**
http://github.com/eaydin/cr2fits

A script to convert RAW images (canon, nikon etc.) to FITS images. I think this'll be useful for professional or amateur astronomers who happen to work with DSLR cameras and want to process their images with some astronomical tool (IRAF?).
It extracts only one color channel of the RAW image, and writes the necessary EXIF information to the FITS header.

Dependencies :

- Python 2.6.x or later.
- astropy: Older versions cr2fits (1.0.3 and earlier) depended on PyFITS. From 2.0.0 and on it migrated to astropy. It uses astropy.io.fits which is basically the same as PyFITS for now.
- dcraw: Try getting the latest version of this. Usually the ones in repositories is not the latest so it's possible that it'll convert your RAW images differently, corrupted. Get the latest version here : http://www.cybercom.net/~dcoffin/dcraw/ Also the one distributed with this package should work.

Usage :

`cr2fits.py <cr2-filename> <color-index>`

- cr2-filename : This will obviously be the name of the file to convert.
- color-index : Can take three values, either 0, 1, 2 which represent Red, Green, Blue respectively.

Outputs :

The script will output 2 files. One PPM file, and one FITS file. The PPM file is useless if you don’t need it, but the script doesn’t delete it. I’ve left it on purpose, since the script you’re going to call cr2fits can easily handle the job. (ex: your shell script?) The FITS file is what we need, the color channel is also added to the name of the output file.
