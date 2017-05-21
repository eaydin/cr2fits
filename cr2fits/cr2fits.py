#!/usr/bin/python
"""
Convert RAW Camera images such as Canon Raw or Nikon Raw to FITS.

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


class CR2FITS(object):
    """
    The main CR2FITS class.

    Creates an object to read raw images into Numpy Arrays
    and convert them directly to FITS files
    """

    def __init__(self, filename, color):
        """Initialize the object."""
        self.filename = filename
        self.colorInput = color
        self.pbm_bytes = None
        self.colors = {0: "Red", 1: "Green", 2: "Blue"}

        self.date = None
        self.shutter = None
        self.aperture = None
        self.iso = None
        self.focal = None
        self.original_file = None
        self.camera = None

        self.im_ppm = None
        self.im_channel = None

    def _read_cr2(self):
        """Run the dcraw command and read it as BytesIO."""
        self.pbm_bytes = BytesIO(subprocess.check_output(["dcraw", "-W", "-j",
                                                          "-6", "-c",
                                                          self.filename]))

    def _read_exif(self):
        """Read the EXIT data from RAW image."""
        # Getting the EXIF of CR2 with dcraw
        p = subprocess.Popen(["dcraw", "-i", "-v", self.filename],
                             stdout=subprocess.PIPE)
        cr2header = p.communicate()[0].decode("utf-8")

        # Catching the Timestamp
        m = re.search('(?<=Timestamp:).*', cr2header)
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

        self.date = datetime.datetime(int(date1[4]), months[date1[1]],
                                      int(date1[2]),
                                      int(date1[3].split(':')[0]),
                                      int(date1[3].split(':')[1]),
                                      int(date1[3].split(':')[2]))
        self.date = '{0:%Y-%m-%d %H:%M:%S}'.format(self.date)

        # Catching the Shutter Speed
        m = re.search('(?<=Shutter:).*(?=sec)', cr2header)
        self.shutter = m.group(0).strip()

        # Catching the Aperture
        m = re.search('(?<=Aperture: f/).*', cr2header)
        self.aperture = m.group(0).strip()

        # Catching the ISO Speed
        m = re.search('(?<=ISO speed:).*', cr2header)
        self.iso = m.group(0).strip()

        # Catching the Focal length
        m = re.search('(?<=Focal length: ).*(?=mm)', cr2header)
        self.focal = m.group(0).strip()

        # Catching the Original Filename of the cr2
        m = re.search('(?<=Filename:).*', cr2header)
        self.original_file = m.group(0).strip()

        # Catching the Camera Type
        m = re.search('(?<=Camera:).*', cr2header)
        self.camera = m.group(0).strip()

    def read_pbm(self, filename):
        """
        PBM to Numpy Array.

        Reads the NetPBM file and returns a Numpy array

        arguments
        ---------
        filename: Filename or file-like object

        returns
        -------
        Numpy Array

        """
        return NetpbmFile(filename).asarray()

    def get_color(self, image, index):
        """
        Get specific color of the image.

        arguments
        ---------
        image: Numpy Array
        index: Integer, 0,1,2 for R,G,B respectively

        returns
        -------
        Numpy Array

        """
        return image[:, :, index]

    def create_fits(self, image):
        """
        Create FITS file from Numpy Array.

        arguments
        ---------
        image: Numpy Array

        returns
        -------
        Primary HDU: Either PyFITS object or astropy.io.fits object

        """
        hdu = fits.PrimaryHDU(self.im_channel)
        hdu.header.set('OBSTIME', self.date)
        hdu.header.set('EXPTIME', self.shutter)
        hdu.header.set('APERTUR', self.aperture)
        hdu.header.set('ISO', self.iso)
        hdu.header.set('FOCAL', self.focal)
        hdu.header.set('ORIGIN', self.original_file)
        hdu.header.set('FILTER', self.colors[colorInput])
        hdu.header.set('CAMERA', self.camera)
        hdu.header.add_comment('FITS File Created with cr2fits.py\
                               available at {0}'.format(sourceweb))
        hdu.header.add_comment('cr2fits.py version {0}'.format(__version__))
        hdu.header.add_comment('EXPTIME is in seconds.')
        hdu.header.add_comment('APERTUR is the ratio as in f/APERTUR')
        hdu.header.add_comment('FOCAL is in mm')

        return hdu

    def _generate_destination(self, filename, colorindex):
        return filename.split('.')[0] + "-" + \
               self.colors[colorindex][0] + ".fits"

    def write_fits(self, hdu, destination):
        """
        Write FITS object to destination.

        arguments
        ---------
        hdu: FITS object
        destination: Filepath to write the FITS file to (string).

        returns
        -------
        Void

        """
        hdu.writeto(destination)

    def convert(self):
        """Convert RAW to FITS."""
        self._read_cr2()
        self._read_exif()
        im_ppm = self.read_pbm(self.pbm_bytes)
        im_channel = self.get_color(im_ppm, self.colorInput)
        fits_image = self.create_fits(im_channel)
        dest = self._generate_destination(self.filename, self.colorInput)
        self.write_fits(fits_image, dest)


if __name__ == '__main__':

    try:
        cr2FileName = sys.argv[1]
        colorInput = int(sys.argv[2])  # 0=R 1=G 2=B
    except:
        print("./cr2fits.py <cr2filename> <color-index>")
        print("The <color-index> can take one of \
              3 values: 0,1,2 for R,G,B respectively.")
        print("Example:\n\t$ ./cr2fits.py myimage.cr2 1")
        print("The above example will create 2 outputs.")
        print("\tmyimage.ppm: The PPM, which you can delete.")
        print("\tmyimage-G.fits: The FITS image in the Green channel, \
              which is the purpose!")
        print("For details: {0}".format(sourceweb))
        print("Version: {0}".format(__version__))
        raise SystemExit

    if sys.version_info[0] > 2:
        # A nasty hack to work around xrange / range diff for Python 2vs3
        xrange = range
        basestring = str

        def unicode(x):
            """Dirty hack for Python 3."""
            return str(x, 'ascii')

    colors = {0: "Red", 1: "Green", 2: "Blue"}
    colorState = any([True for i in colors.keys() if i == colorInput])
    if not colorState:
        print("ERROR: Color value can be set as 0:Red, 1:Green, 2:Blue.")
        raise SystemExit

    cr2 = CR2FITS(cr2FileName, colorInput)
    cr2.convert()
