#!/usr/bin/python
"""
Convert RAW Camera images such as Canon Raw or Nikon Raw to FITS
Details at https://github.com/eaydin/cr2fits
"""

sourceweb = "https://github.com/eaydin/cr2fits"
__version__ = "2.0.0"

try:
    import pyfits as fits
    pyfits_loaded = True
except ImportError:
    pyfits_loaded = False

if not pyfits_loaded:
    try:
        from astopy.io import fits
    except ImportError:
        print("Error: Missing module. Either install PyFITS or Astropy")
        raise SystemExit

try:
    import numpy as np
    import subprocess
    import sys
    import re
    import datetime
    from netpbmfile import NetpbmFile
    from io import BytesIO

except Exception as err:
    print("Error: Missing some libraries!")
    print("Error msg: {0}".format(str(err)))
    raise SystemExit

try:
    cr2FileName = sys.argv[1]
    colorInput = int(sys.argv[2])  # 0=R 1=G 2=B
except:
    print("./cr2fits.py <cr2filename> <color-index>")
    print("The <color-index> can take 3 values: 0,1,2 for R,G,B respectively.")
    print("Example:\n\t$ ./cr2fits.py myimage.cr2 1")
    print("The above example will create 2 outputs.")
    print("\tmyimage.ppm: The PPM, which you can delete.")
    print("\tmyimage-G.fits: The FITS image in the Green channel, \
          which is the purpose!")
    print("For details: http://github.com/eaydin/cr2fits")
    print("Version: {0}".format(__version__))
    raise SystemExit

if sys.version_info[0] == "3":
    # A nasty hack to work around xrange / range diff for Python 2vs3
    xrange = range

colors = {0: "Red", 1: "Green", 2: "Blue"}
colorState = any([True for i in colors.keys() if i == colorInput])
if not colorState:
    print("ERROR: Color value can be set as 0:Red, 1:Green, 2:Blue.")
    raise SystemExit

print("Reading file {0}...".format(cr2FileName))
try:
    # Converting the CR2 to PPM

    ppm_bytes = BytesIO(subprocess.check_output(["dcraw", "-6", "-j", "-W", "-c", cr2FileName]))

    # Getting the EXIF of CR2 with dcraw
    p = subprocess.Popen(["dcraw", "-i", "-v", cr2FileName], stdout=subprocess.PIPE)
    cr2header = p.communicate()[0]

    # Catching the Timestamp
    m = re.search(b'(?<=Timestamp:).*', cr2header)
    date1 = m.group(0).split()
    months = {
              'Jan': 1,
              'Feb': 2,
              'Mar': 3,
              'Apr': 4,
              'May': 5,
              'Jun': 6,
              'Jul': 7,
              'Aug': 8,
              'Sep': 9,
              'Oct': 10,
              'Nov': 11,
              'Dec': 12
              }
    date = datetime.datetime(int(date1[4]), months[date1[1]], int(date1[2]),
                             int(date1[3].split(':')[0]),
                             int(date1[3].split(':')[1]),
                             int(date1[3].split(':')[2]))
    date = '{0:%Y-%m-%d %H:%M:%S}'.format(date)

    # Catching the Shutter Speed
    m = re.search(b'(?<=Shutter:).*(?=sec)', cr2header)
    shutter = m.group(0).strip()

    # Catching the Aperture
    m = re.search(b'(?<=Aperture: f/).*', cr2header)
    aperture = m.group(0).strip()

    # Catching the ISO Speed
    m = re.search(b'(?<=ISO speed:).*', cr2header)
    iso = m.group(0).strip()

    # Catching the Focal length
    m = re.search(b'(?<=Focal length: ).*(?=mm)', cr2header)
    focal = m.group(0).strip()

    # Catching the Original Filename of the cr2
    m = re.search(b'(?<=Filename:).*', cr2header)
    original_file = m.group(0).strip()

    # Catching the Camera Type
    m = re.search(b'(?<=Camera:).*', cr2header)
    camera = m.group(0).strip()

except Exception as err:
    print("ERROR: Something went wrong with dcraw. Do you even have dcraw?")
    print("Error message: {0}".format(str(err)))
    raise SystemExit

print("Reading the PPM output...")
try:
    # Reading the PPM
    im_ppm = NetpbmFile(ppm_bytes).asarray()
except Exception as err:
    print("ERROR : Something went wrong while reading the PPM file.")
    print("Error message: {0}".format(str(err)))
    raise SystemExit

print("Extracting {0} color channels... (may take a while)".format(colors[colorInput]))

try:
    # Slicing the relevant color only
    im_green = im_ppm[:, :, colorInput]

except Exception as err:
    print("ERROR: Something went wrong while extracting color channels.")
    print("Error message: {0}".format(str(err)))
    raise SystemExit

print("Creating the FITS file...")

try:
    # Creating the FITS File
    hdu = fits.PrimaryHDU(im_green)
    hdu.header.set('OBSTIME', date)
    hdu.header.set('EXPTIME', shutter)
    hdu.header.set('APERTUR', aperture)
    hdu.header.set('ISO', iso)
    hdu.header.set('FOCAL', focal)
    hdu.header.set('ORIGIN', original_file)
    hdu.header.set('FILTER', colors[colorInput])
    hdu.header.set('CAMERA', camera)
    hdu.header.add_comment('FITS File Created with cr2fits.py available at {0}'.format(sourceweb))
    hdu.header.add_comment('cr2fits.py version {0}'.format(__version__))
    hdu.header.add_comment('EXPTIME is in seconds.')
    hdu.header.add_comment('APERTUR is the ratio as in f/APERTUR')
    hdu.header.add_comment('FOCAL is in mm')
except Exception as err:
    print("ERROR : Something went wrong while creating the FITS file.")
    print("Error message: {0}".format(str(err)))
    raise SystemExit

print("Writing the FITS file...")
try:
    hdu.writeto(cr2FileName.split('.')[0]+"-"+colors[colorInput][0]+'.fits')
except Exception as err:
    print("ERROR: Something went wrong while writing the FITS file. Maybe it already exists?")
    print("Error message: {0}".format(str(err)))
    raise SystemExit

print("Conversion successful!")
