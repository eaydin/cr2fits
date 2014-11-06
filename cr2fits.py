#!/usr/bin/python
# -*- coding: utf-8 -*-

# 3rd attempt
# 15th Feb 2012, 09:38AM
# http://eayd.in
# http://github.com/eaydin/cr2fits

### This script is redistributable in anyway.
### But it includes netpbmfile.py which is NOT written by M. Emre Aydin.
### It has its own copyright and it has been stated in the source code.
### BUT, there's nothing to worry about usage, laws etc.
### Enjoy.

sourceweb = "http://github.com/eaydin/cr2fits"
version = "1.0.3"

try :    
    from copy import deepcopy
    import numpy, pyfits, subprocess, sys, re, datetime, math
    
except :
    print("ERROR : Missing some libraries!")
    print("Check if you have the following :\n\tnumpy\n\tpyfits\n\tdcraw")
    print("For details : %s" % sourceweb)
    raise SystemExit

### --- NETPBMFILE SOURCE CODE --- ###

# Copyright (c) 2011, Christoph Gohlke
# Copyright (c) 2011, The Regents of the University of California
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
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
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

__all__ = ['NetpbmFile']

class NetpbmFile(object):
    """Read and write Netpbm PAM, PBM, PGM, PPM, files."""

    _types = {b'P1': b'BLACKANDWHITE', b'P2': b'GRAYSCALE', b'P3': b'RGB',
              b'P4': b'BLACKANDWHITE', b'P5': b'GRAYSCALE', b'P6': b'RGB',
              b'P7 332': b'RGB', b'P7': b'RGB_ALPHA'}

    def __init__(self, arg=None, **kwargs):
        """Initialize instance from filename, open file, or numpy array."""
        for attr in ('header', 'magicnum', 'width', 'height', 'maxval',
                     'depth', 'tupltypes', '_filename', '_fileid', '_data'):
            setattr(self, attr, None)
        if arg is None:
            self._fromdata([], **kwargs)
        elif isinstance(arg, basestring):
            self._fileid = open(arg, 'rb')
            self._filename = arg
            self._fromfile(self._fileid, **kwargs)
        elif hasattr(arg, 'seek'):
            self._fromfile(arg, **kwargs)
            self._fileid = arg
        else:
            self._fromdata(arg, **kwargs)

    def asarray(self, copy=True, cache=False, **kwargs):
        """Return image data from file as numpy array."""
        data = self._data
        if data is None:
            data = self._read_data(self._fileid, **kwargs)
            if cache:
                self._data = data
            else:
                return data
        return deepcopy(data) if copy else data

    def write(self, arg, **kwargs):
        """Write instance to file."""
        if hasattr(arg, 'seek'):
            self._tofile(arg, **kwargs)
        else:
            with open(arg, 'wb') as fid:
                self._tofile(fid, **kwargs)

    def close(self):
        """Close open file. Future asarray calls might fail."""
        if self._filename and self._fileid:
            self._fileid.close()
            self._fileid = None

    def __del__(self):
        self.close()

    def _fromfile(self, fileid):
        """Initialize instance from open file."""
        fileid.seek(0)
        data = fileid.read(4096)
        if (len(data) < 7) or not (b'0' < data[1:2] < b'8'):
            raise ValueError("Not a Netpbm file:\n%s" % data[:32])
        try:
            self._read_pam_header(data)
        except Exception:
            try:
                self._read_pnm_header(data)
            except Exception:
                raise ValueError("Not a Netpbm file:\n%s" % data[:32])

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

    def _read_data(self, fileid, byteorder='>'):
        """Return image data from open file as numpy array."""
        fileid.seek(len(self.header))
        data = fileid.read()
        dtype = 'u1' if self.maxval < 256 else byteorder + 'u2'
        depth = 1 if self.magicnum == b"P7 332" else self.depth
        shape = [-1, self.height, self.width, depth]
        size = numpy.prod(shape[1:])
        if self.magicnum in b"P1P2P3":
            data = numpy.array(data.split(None, size)[:size], dtype)
            data = data.reshape(shape)
        elif self.maxval == 1:
            shape[2] = int(math.ceil(self.width / 8))
            data = numpy.frombuffer(data, dtype).reshape(shape)
            data = numpy.unpackbits(data, axis=-2)[:, :, :self.width, :]
        else:
            data = numpy.frombuffer(data, dtype)
            data = data[:size * (data.size // size)].reshape(shape)
        if data.shape[0] < 2:
            data = data.reshape(data.shape[1:])
        if data.shape[-1] < 2:
            data = data.reshape(data.shape[:-1])
        if self.magicnum == b"P7 332":
            rgb332 = numpy.array(list(numpy.ndindex(8, 8, 4)), numpy.uint8)
            rgb332 *= [36, 36, 85]
            data = numpy.take(rgb332, data, axis=0)
        return data

    def _fromdata(self, data, maxval=None):
        """Initialize instance from numpy array."""
        data = numpy.array(data, ndmin=2, copy=True)
        if data.dtype.kind not in "uib":
            raise ValueError("not an integer type: %s" % data.dtype)
        if data.dtype.kind == 'i' and numpy.min(data) < 0:
            raise ValueError("data out of range: %i" % numpy.min(data))
        if maxval is None:
            maxval = numpy.max(data)
            maxval = 255 if maxval < 256 else 65535
        if maxval < 0 or maxval > 65535:
            raise ValueError("data out of range: %i" % maxval)
        data = data.astype('u1' if maxval < 256 else '>u2')
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

    def _tofile(self, fileid, pam=False):
        """Write Netbm file."""
        fileid.seek(0)
        fileid.write(self._header(pam))
        data = self.asarray(copy=False)
        if self.maxval == 1:
            data = numpy.packbits(data, axis=-1)
        data.tofile(fileid)

    def _header(self, pam=False):
        """Return file header as byte string."""
        if pam or self.magicnum == b'P7':
            header = "\n".join(("P7",
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

    def __str__(self):
        """Return information about instance."""
        return unicode(self.header)


if sys.version_info[0] > 2:
    basestring = str
    unicode = lambda x: str(x, 'ascii')

### --- END OF NETPBMFILE SOURCE CODE --- ###

### CR2FITS SOURCE CODE ###


try :
    cr2FileName = sys.argv[1]
    colorInput = int(sys.argv[2]) # 0=R 1=G 2=B
except :
    print("ERROR : You probably don't know how to use it?")
    print("./cr2fits.py <cr2filename> <color-index>")
    print("The <color-index> can take 3 values:0,1,2 for R,G,B respectively.")
    print("Example :\n\t$ ./cr2fits.py myimage.cr2 1")
    print("The above example will create 2 outputs.")
    print("\tmyimage.ppm : The PPM, which you can delete.")
    print("\tmyimage-G.fits : The FITS image in the Green channel, which is the purpose!")
    print("For details : http://github.com/eaydin/cr2fits")
    print("Version : %s" % version) 
    raise SystemExit

colors = {0:"Red",1:"Green",2:"Blue"}
colorState = any([True for i in colors.keys() if i == colorInput])

if colorState == False :
    print("ERROR : Color value can be set as 0:Red, 1:Green, 2:Blue.")
    raise SystemExit    

print("Reading file %s...") % cr2FileName
try : 
    #Converting the CR2 to PPM
    p = subprocess.Popen(["dcraw","-6","-j","-W",cr2FileName]).communicate()[0]

    #Getting the EXIF of CR2 with dcraw
    p = subprocess.Popen(["dcraw","-i","-v",cr2FileName],stdout=subprocess.PIPE)
    cr2header = p.communicate()[0]

    #Catching the Timestamp
    m = re.search('(?<=Timestamp:).*',cr2header)
    date1=m.group(0).split()
    months = { 'Jan' : 1, 'Feb' : 2, 'Mar' : 3, 'Apr' : 4, 'May' : 5, 'Jun' : 6, 'Jul' : 7, 'Aug' : 8, 'Sep' : 9, 'Oct' : 10, 'Nov' : 11, 'Dec' : 12 }
    date = datetime.datetime(int(date1[4]),months[date1[1]],int(date1[2]),int(date1[3].split(':')[0]),int(date1[3].split(':')[1]),int(date1[3].split(':')[2]))
    date ='{0:%Y-%m-%d %H:%M:%S}'.format(date)

    #Catching the Shutter Speed
    m = re.search('(?<=Shutter:).*(?=sec)',cr2header)
    shutter = m.group(0).strip()

    #Catching the Aperture
    m = re.search('(?<=Aperture: f/).*',cr2header)
    aperture = m.group(0).strip()

    #Catching the ISO Speed
    m = re.search('(?<=ISO speed:).*',cr2header)
    iso = m.group(0).strip()

    #Catching the Focal length
    m = re.search('(?<=Focal length: ).*(?=mm)',cr2header)
    focal = m.group(0).strip()

    #Catching the Original Filename of the cr2
    m = re.search('(?<=Filename:).*',cr2header)
    original_file = m.group(0).strip()
    
    #Catching the Camera Type
    m = re.search('(?<=Camera:).*',cr2header)
    camera = m.group(0).strip()
    
except :
    print("ERROR : Something went wrong with dcraw. Do you even have dcraw?")
    raise SystemExit

print("Reading the PPM output...")
try :
    #Reading the PPM
    ppm_name = cr2FileName.split('.')[0] + '.ppm'
    im_ppm = NetpbmFile(ppm_name).asarray()
except :
    print("ERROR : Something went wrong while reading the PPM file.")
    raise SystemExit

print("Extracting %s color channels... (may take a while)" % colors[colorInput]) 
try :
    #Extracting the Green Channel Only
    im_green = numpy.zeros((im_ppm.shape[0],im_ppm.shape[1]),dtype=numpy.uint16)
    for row in xrange(0,im_ppm.shape[0]) :
        for col in xrange(0,im_ppm.shape[1]) :
            im_green[row,col] = im_ppm[row,col][colorInput]
except :
    print("ERROR : Something went wrong while extracting color channels.")
    raise SystemExit

print("Creating the FITS file...")
try :
#Creating the FITS File
    hdu = pyfits.PrimaryHDU(im_green)
    hdu.header.set('OBSTIME',date)
    hdu.header.set('EXPTIME',shutter)
    hdu.header.set('APERTUR',aperture)
    hdu.header.set('ISO',iso)
    hdu.header.set('FOCAL',focal)
    hdu.header.set('ORIGIN',original_file)
    hdu.header.set('FILTER',colors[colorInput])
    hdu.header.set('CAMERA',camera)
    hdu.header.add_comment('FITS File Created with cr2fits.py available at %s'%(sourceweb))
    hdu.header.add_comment('cr2fits.py version %s'%(version))
    hdu.header.add_comment('EXPTIME is in seconds.')
    hdu.header.add_comment('APERTUR is the ratio as in f/APERTUR')
    hdu.header.add_comment('FOCAL is in mm')    
except : 
    print("ERROR : Something went wrong while creating the FITS file.")
    raise SystemExit

print("Writing the FITS file...")
try :
    hdu.writeto(cr2FileName.split('.')[0]+"-"+colors[colorInput][0]+'.fits')
except :
    print("ERROR : Something went wrong while writing the FITS file. Maybe it already exists?")
    raise SystemExit
    
print("Conversion successful!")
