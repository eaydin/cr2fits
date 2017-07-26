#!/usr/bin/python
"""
Convert RAW Camera images such as Canon Raw or Nikon Raw to FITS.

Details at https://github.com/eaydin/cr2fits
"""

sourceweb = "https://github.com/eaydin/cr2fits"
__version__ = "2.1.0"

try:
    import pyfits as fits
    pyfits_loaded = True
except ImportError:
    pyfits_loaded = False

if not pyfits_loaded:
    try:
        from astropy.io import fits
    except ImportError:
        print("Error: Missing module. Either install PyFITS or Astropy")
        raise SystemExit

try:
    import numpy as np
    import subprocess
    import sys
    import re
    import datetime
    import os.path
    from io import BytesIO
    import math
    from copy import deepcopy

except Exception as err:
    print("Error: Missing some libraries!")
    print("Error msg: {0}".format(str(err)))
    raise SystemExit


class NetpbmFile(object):
    """Read and write Netpbm PAM, PBM, PGM, PPM, files."""

    # This class was written by Christoph Gohlke,
    # Modified by M. Emre Aydin to include in cr2fits
    # NetpbmFile's LICENSE is below
    # :Author:
    #   `Christoph Gohlke <http://www.lfd.uci.edu/~gohlke/>`_
    #
    # :Organization:
    #   Laboratory for Fluorescence Dynamics, University of California, Irvine
    #
    # :Version: 2016.02.24

    # Copyright (c) 2011-2016, Christoph Gohlke
    # Copyright (c) 2011-2016, The Regents of the University of California
    # Produced at the Laboratory for Fluorescence Dynamics.
    # All rights reserved.
    #
    # Redistribution and use in source and binary forms, with or without
    # modification, are permitted provided that the following conditions
    # are met:
    #
    # * Redistributions of source code must retain the above copyright
    #   notice, this list of conditions and the following disclaimer.
    # * Redistributions in binary form must reproduce the above copyright
    #   notice, this list of conditions and the following disclaimer in the
    #   documentation and/or other materials provided with the distribution.
    # * Neither the name of the copyright holders nor the names of any
    #   contributors may be used to endorse or promote products derived
    #   from this software without specific prior written permission.
    #
    # THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
    # "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
    # TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
    # PARTICULAR PURPOSE RE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER
    # OR A CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
    # SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED
    # TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA,
    # OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
    # LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
    # NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
    # SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

    _types = {b'P1': b'BLACKANDWHITE', b'P2': b'GRAYSCALE', b'P3': b'RGB',
              b'P4': b'BLACKANDWHITE', b'P5': b'GRAYSCALE', b'P6': b'RGB',
              b'P7 332': b'RGB', b'P7': b'RGB_ALPHA'}

    def __init__(self, filename):
        """Initialize instance from filename or open file."""
        for attr in ('header', 'magicnum', 'width', 'height', 'maxval',
                     'depth', 'tupltypes', '_filename', '_fh', '_data'):
            setattr(self, attr, None)
        if filename is None:
            return
        if hasattr(filename, 'seek'):
            self._fh = filename
        else:
            self._fh = open(filename, 'rb')
            self._filename = filename

        self._fh.seek(0)
        data = self._fh.read(4096)
        if (len(data) < 7) or not (b'0' < data[1:2] < b'8'):
            raise ValueError("Not a Netpbm file:\n%s" % data[:32])
        try:
            self._read_pam_header(data)
        except Exception:
            try:
                self._read_pnm_header(data)
            except Exception:
                raise ValueError("Not a Netpbm file:\n%s" % data[:32])

    @classmethod
    def fromdata(cls, data, maxval=None):
        """Initialize instance from numpy array."""
        data = np.array(data, ndmin=2, copy=True)
        if data.dtype.kind not in "uib":
            raise ValueError("not an integer type: %s" % data.dtype)
        if data.dtype.kind == 'i' and np.min(data) < 0:
            raise ValueError("data out of range: %i" % np.min(data))
        if maxval is None:
            maxval = np.max(data)
            maxval = 255 if maxval < 256 else 65535
        if maxval < 0 or maxval > 65535:
            raise ValueError("data out of range: %i" % maxval)
        data = data.astype('u1' if maxval < 256 else '>u2')

        self = cls(None)
        self._data = data
        if data.ndim > 2 and data.shape[-1] in (3, 4):
            self.depth = data.shape[-1]
            self.width = data.shape[-2]
            self.height = data.shape[-3]
            self.magicnum = b'P7' if self.depth == 4 else b'P6'
        else:
            self.depth = 1
            self.width = data.shape[-1]
            self.height = data.shape[-2]
            self.magicnum = b'P5' if maxval > 1 else b'P4'
        self.maxval = maxval
        self.tupltypes = [self._types[self.magicnum]]
        self.header = self._header()
        return self

    def asarray(self, copy=True, cache=False, byteorder='>'):
        """Return image data from file as numpy array."""
        data = self._data
        if data is None:
            data = self._read_data(self._fh, byteorder=byteorder)
            if cache:
                self._data = data
            else:
                return data
        return deepcopy(data) if copy else data

    def write(self, filename, pam=False):
        """Write instance to file."""
        if hasattr(filename, 'seek'):
            self._tofile(filename, pam=pam)
        else:
            with open(filename, 'wb') as fh:
                self._tofile(fh, pam=pam)

    def close(self):
        """Close open file. Future asarray calls might fail."""
        if self._filename and self._fh:
            self._fh.close()
            self._fh = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def __str__(self):
        """Return information about instance."""
        return unicode(self.header)

    def _read_pam_header(self, data):
        """Read PAM header and initialize instance."""
        regroups = re.search(
            b"(^P7[\n\r]+(?:(?:[\n\r]+)|(?:#.*)|"
            b"(HEIGHT\s+\d+)|(WIDTH\s+\d+)|(DEPTH\s+\d+)|(MAXVAL\s+\d+)|"
            b"(?:TUPLTYPE\s+\w+))*ENDHDR\n)", data).groups()
        self.header = regroups[0]
        self.magicnum = b'P7'
        for group in regroups[1:]:
            key, value = group.split()
            setattr(self, unicode(key).lower(), int(value))
        matches = re.findall(b"(TUPLTYPE\s+\w+)", self.header)
        self.tupltypes = [s.split(None, 1)[1] for s in matches]

    def _read_pnm_header(self, data):
        """Read PNM header and initialize instance."""
        bpm = data[1:2] in b"14"
        regroups = re.search(b"".join((
            b"(^(P[123456]|P7 332)\s+(?:#.*[\r\n])*",
            b"\s*(\d+)\s+(?:#.*[\r\n])*",
            b"\s*(\d+)\s+(?:#.*[\r\n])*" * (not bpm),
            b"\s*(\d+)\s(?:\s*#.*[\r\n]\s)*)")), data).groups() + (1, ) * bpm
        self.header = regroups[0]
        self.magicnum = regroups[1]
        self.width = int(regroups[2])
        self.height = int(regroups[3])
        self.maxval = int(regroups[4])
        self.depth = 3 if self.magicnum in b"P3P6P7 332" else 1
        self.tupltypes = [self._types[self.magicnum]]

    def _read_data(self, fh, byteorder='>'):
        """Return image data from open file as numpy array."""
        fh.seek(len(self.header))
        data = fh.read()
        dtype = 'u1' if self.maxval < 256 else byteorder + 'u2'
        depth = 1 if self.magicnum == b"P7 332" else self.depth
        shape = [-1, self.height, self.width, depth]
        size = np.prod(shape[1:], dtype='int64')
        if self.magicnum in b"P1P2P3":
            data = np.array(data.split(None, size)[:size], dtype)
            data = data.reshape(shape)
        elif self.maxval == 1:
            shape[2] = int(math.ceil(self.width / 8))
            data = np.frombuffer(data, dtype).reshape(shape)
            data = np.unpackbits(data, axis=-2)[:, :, :self.width, :]
        else:
            size *= np.dtype(dtype).itemsize
            data = np.frombuffer(data[:size], dtype).reshape(shape)
        if data.shape[0] < 2:
            data = data.reshape(data.shape[1:])
        if data.shape[-1] < 2:
            data = data.reshape(data.shape[:-1])
        if self.magicnum == b"P7 332":
            rgb332 = np.array(list(np.ndindex(8, 8, 4)), np.uint8)
            rgb332 *= np.array([36, 36, 85], np.uint8)
            data = np.take(rgb332, data, axis=0)
        return data

    def _tofile(self, fh, pam=False):
        """Write Netpbm file."""
        fh.seek(0)
        fh.write(self._header(pam))
        data = self.asarray(copy=False)
        if self.maxval == 1:
            data = np.packbits(data, axis=-1)
        data.tofile(fh)

    def _header(self, pam=False):
        """Return file header as byte string."""
        if pam or self.magicnum == b'P7':
            header = "\n".join((
                "P7",
                "HEIGHT %i" % self.height,
                "WIDTH %i" % self.width,
                "DEPTH %i" % self.depth,
                "MAXVAL %i" % self.maxval,
                "\n".join("TUPLTYPE %s" % unicode(i) for i in self.tupltypes),
                "ENDHDR\n"))
        elif self.maxval == 1:
            header = "P4 %i %i\n" % (self.width, self.height)
        elif self.depth == 1:
            header = "P5 %i %i %i\n" % (self.width, self.height, self.maxval)
        else:
            header = "P6 %i %i %i\n" % (self.width, self.height, self.maxval)
        if sys.version_info[0] > 2:
            header = bytes(header, 'ascii')
        return header


class cr2fits(object):
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
        self.colors = {0: "Red", 1: "Green", 2: "Blue", 3: "Raw"}

        self.date = None
        self.shutter = None
        self.aperture = None
        self.iso = None
        self.focal = None
        self.original_file = None
        self.camera = None

        self.im_ppm = None
        self.im_channel = None

    def read_cr2(self):
        """Run the dcraw command and read it as BytesIO."""
        if self.colorInput == 3:
            self.pbm_bytes = BytesIO(subprocess.check_output(["dcraw", "-D",
                                                              "-4", "-j",
                                                              "-c",
                                                              self.filename]))
        else:
            self.pbm_bytes = BytesIO(subprocess.check_output(["dcraw", "-W",
                                                              "-6", "-j", "-c",
                                                              self.filename]))

    def read_exif(self):
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
        hdu = fits.PrimaryHDU(image)
        hdu.header.set('OBSTIME', self.date)
        hdu.header.set('EXPTIME', self.shutter)
        hdu.header.set('APERTUR', self.aperture)
        hdu.header.set('ISO', self.iso)
        hdu.header.set('FOCAL', self.focal)
        hdu.header.set('ORIGIN', self.original_file)
        hdu.header.set('FILTER', self.colors[self.colorInput])
        hdu.header.set('CAMERA', self.camera)
        hdu.header.add_comment('FITS File Created with cr2fits.py\
                               available at {0}'.format(sourceweb))
        hdu.header.add_comment('cr2fits.py version {0}'.format(__version__))
        hdu.header.add_comment('EXPTIME is in seconds.')
        hdu.header.add_comment('APERTUR is the ratio as in f/APERTUR')
        hdu.header.add_comment('FOCAL is in mm')

        return hdu

    def _generate_destination(self, filename, colorindex):
        """
        Generate destination filename to output FITS.

        Generates the filename to write. Will alternate if file already exists.

        arguments
        ---------
        filename: input filename (string).
        colorindex: the colorindex (integer).

        returns
        -------
        filename: output filename (string).

        """
        if colorindex == 3:
            channel_name = "RAW"
        else:
            channel_name = self.colors[colorindex][0]

        filename = "".join(filename.split('.')[:-1])

        writename = filename + "-" + channel_name + ".fits"
        if os.path.isfile(writename):
            for i in range(1, 9000000):
                # Crashes after 9million files with same name but what the hell
                writename = "{fn}-{ch}-{i}.fits".format(fn=filename,
                                                        ch=channel_name, i=i)
                if not os.path.isfile(writename):
                    break
        return writename

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
        self.read_cr2()
        self.read_exif()
        im_ppm = self.read_pbm(self.pbm_bytes)
        if self.colorInput == 3:
            im_channel = im_ppm
        else:
            im_channel = self.get_color(im_ppm, self.colorInput)
        fits_image = self.create_fits(im_channel)
        dest = self._generate_destination(self.filename, self.colorInput)
        self.write_fits(fits_image, dest)


if __name__ == '__main__':

    try:
        cr2FileName = sys.argv[1]
        colorInput = int(sys.argv[2])
    except:
        print("./cr2fits.py <cr2filename> <color-index>")
        print("The <color-index> can take one of \
              4 values: 0,1,2,3 for R,G,B and Unscaled Raw respectively.")
        print("Example:\n\t$ ./cr2fits.py myimage.cr2 1")
        print("The above example will create a fits file.")
        print("\tmyimage-G.fits: The FITS image in the Green channel, \
              which is the purpose!")
        print("For details: {0}".format(sourceweb))
        print("Version: {0}".format(__version__))
        raise SystemExit

    if sys.version_info[0] > 2:
        # A nasty hack to work around Python 3 compatilibity
        basestring = str

        def unicode(x):
            """Dirty hack for Python 3."""
            return str(x, 'ascii')

    colors = {0: "Red", 1: "Green", 2: "Blue", 3: "Raw"}
    colorState = any([True for i in colors.keys() if i == colorInput])
    if not colorState:
        print("ERROR: Color value can be set as 0:Red, 1:Green, 2:Blue, 3:Raw")
        raise SystemExit

    cr2 = cr2fits(cr2FileName, colorInput)
    cr2.convert()
