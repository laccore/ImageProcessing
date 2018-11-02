# LacCore/CSDCO
# xrf.py
#
# Prepare a raw XRF radiograph TIFF by doing the following:
# 1. Increase contrast by finding the range of colors in the source image,
# mapping all pixels <= minimum to black and >= maximum to white, and
# interpolating for pixels between min and max.
# 2. Rotate image 180 degrees.
# 3. Add standard XRF ruler image below XRF image.
# 4. Save resulting image in JPEG format.
#
# Note: raw input XRF images are 16-bit grayscale TIFFs. PIL/Pillow
# loads these happily, but can't seem to save them as 16-bit...values
# are always forced to 8-bit, so precision is lost. But in order to
# convert to RGB mode, which PIL requires to save as JPEG, that precision
# is lost anyway (8-bit components and everything is grayscale so 
# R, G, and B will all be the same).

import os
from PIL import Image

from common import create_dirs

ProgressListener = None

def setProgressListener(pl):
    global ProgressListener
    ProgressListener = pl
    ProgressListener.clear()

def reportProgress(value, text):
    global ProgressListener
    if ProgressListener:
        ProgressListener.setValueAndText(value, text)

class ContrastAdjuster:
    def __init__(self, minv, maxv, gamma, pixeldepth):
        self.minv = minv
        self.maxv = maxv
        self._interval = self.maxv - self.minv
        self._invgamma = 1.0/gamma
        self.pixeldepth = pixeldepth

    def new_level(self, value):
        if value <= self.minv:
            return 0.0
        if value >= self.maxv:
            return 1.0
        return ((value - self.minv) / float(self._interval)) ** self._invgamma

    def adjust(self, val):
        return int(self.pixeldepth * self.new_level(val))


# returns a copy of img with contrast maximized
def adjust_contrast(img, gamma):
    pix = list(img.getdata())
    pmin, pmax = min(pix), max(pix)
    adjuster = ContrastAdjuster(pmin, pmax, gamma, 2**8-1)
    adj_pix = [adjuster.adjust(p) for p in pix]
    adj_img = Image.new("RGB", (img.width, img.height))
    adj_img.putdata([(v,v,v) for v in adj_pix])
    return adj_img

# adjust contrast, rotate, add ruler to imgPath, save to destDir
def prepare_xrf(imgPath, rulerPath, gamma, outputBaseName, destDir):
    baseProgStr = "Processing {}...".format(imgPath)
    reportProgress(0, baseProgStr)
    RadiographDir = 'radiograph'
    create_dirs(destDir, [RadiographDir])

    img = Image.open(imgPath)
    reportProgress(25, baseProgStr + "adjusting levels")
    adj_img = adjust_contrast(img, gamma)
    adj_img = adj_img.rotate(180)
    ruler_img = Image.open(rulerPath)
    reportProgress(50, baseProgStr + "adding ruler")
    dest_img = Image.new("RGB", (adj_img.width, adj_img.height + ruler_img.height))
    dest_img.paste(adj_img)
    dest_img.paste(ruler_img, (0, adj_img.height))
    reportProgress(75, baseProgStr + "writing to JPEG")
    destPath = os.path.join(destDir, RadiographDir, outputBaseName + ".jpg")
    dest_img.save(destPath)
