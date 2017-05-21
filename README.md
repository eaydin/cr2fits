cr2fits
=======

cr2fits.py version **2.1.0**  
https://github.com/eaydin/cr2fits

[![DOI](https://zenodo.org/badge/3470172.svg)](https://zenodo.org/badge/latestdoi/3470172)

A script to convert RAW images (Canon, Nikon etc.) to FITS images. It extracts only one color channel of the RAW image, and writes the necessary EXIF information to the FITS header.

# Dependencies

- Python 2.7 or Python >= 3.2
- PyFITS or astropy: Older versions cr2fits (1.0.3 and earlier) depended on PyFITS. From 2.0.0 and on it added support for astropy. It uses astropy.io.fits which is basically the same as PyFITS for now. Favors PyFITS over astropy if you have both, since it is faster to load.
- dcraw: Try getting the latest version of this. Usually the ones in repositories is not the latest so it's possible that it'll convert your RAW images differently, corrupted. Get the latest version here : http://www.cybercom.net/~dcoffin/dcraw/ Also the one distributed with this package should work.

# Compiling dcraw:

Either use `gcc -o dcraw -O4 dcraw.c -lm -ljasper -ljpeg -llcms2` or `gcc -o dcraw -O4 dcraw.c -lm -DNODEPS` to compile it.  
You can then copy `dcraw` to your path (ex. `/usr/local/bin`). In order to copy to your path, you'll probably need root privileges.

# Usage

`cr2fits.py <cr2-filename> <color-index>`

- cr2-filename: This will obviously be the name of the file to convert.
- color-index: Can take one of four values, either 0, 1, 2, 3 which represent Red, Green, Blue and Unscaled Raw respectively.

If you want to use it as a module:

```
from cr2fits import cr2fits

# Assuming there's a test.cr2 in the current directory
# And we want the Blue Channel
a = cr2fits("test.cr2", 2)

# Read into the raw image
a.read_cr2()

# Now you have a.pbm_bytes which is the output of dcraw
# Get the EXIF data
a.read_exit()

# Now you have values such as a.shutter, a.date, a.iso ...
# Convert dcraw output to Numpy Array using netpbm
im_ppm = a.read_pbm(a.pbm_bytes)

# Since we want only one channel (ex. Blue) use get_color
im_blue = a.get_color(im_ppm, a.colorInput)

# Create FITS file from Blue Image and EXIF data
fits_image = a.create_fits(im_blue)

# If you want to write output, _generate_destination gets filename
dest = a._generate_destination(a.filename, a.colorInput)

# Write FITS file to generated destination (or elsewhere)
a.write_fits(fits_image, dest)
```

Also, the method convert does all this for you.

```
from cr2fits import cr2fits
a = cr2fits("test.cr2", 2)
a.convert()
```

# Output

The script will output the FITS file, added the color channel to the name of the output.

# Change log

## 2.1.0
- Added support for unscaled raw output.
- Fixed output name detection fails with dot's (.) in the name.
- Detects if output filename exists and gives alternative name

## 2.0.0
- Added support for astropy
- Added support for usage as a module
- Use Numpy slicing instead of looping
- Direct dcraw output to BytesIO object, avoiding the I/O for the unused PPM file
- Updated license

# todo
- Add support for configparser
- Add support for 3D FITS files: an idea from the fork by [@mireianievas](https://github.com/mireianievas)
- Add support for multiple file inputs
