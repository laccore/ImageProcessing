# LacCore/CSDCO
# xrf.py
#
# Prepare a raw XRF radiograph TIFF by doing the following:
# 1. Rotate image 180 degrees.
# 2. Increase contrast by finding the range of colors in the source image,
# mapping all pixels <= minimum to black and >= maximum to white, and
# interpolating for pixels between min and max.
# 3. Add ruler image below XRF image.
# 4. Save resulting image in TIFF format.

import os
import cv2 # OpenCV
import numpy

from common import create_dirs, get_color_depth, get_component_count, UnexpectedColorDepthError, RulerTooShortError, UnexpectedComponentCountError

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
        # print("val = {}".format(val))
        return int(self.pixeldepth * self.new_level(val))

# Return min and max pixel value in img.
def get_pixel_range(img):
    pmin = None
    pmax = None
    for row_idx in range(len(img)):
        rmin = min(img[row_idx])
        rmax = max(img[row_idx])
        if pmin is None or rmin < pmin:
            pmin = rmin
        if pmax is None or rmax > pmax:
            pmax = rmax
    return pmin, pmax

# Count unique pixels in image. Slow.
def count_unique_pixels(img):
    pixs = []
    for row_idx in range(len(img)):
        for p in img[row_idx]:
            if p not in pixs:
                pixs.append(p)
    return len(pixs)

# returns a copy of img with contrast maximized
def adjust_contrast(img, colorDepth, gamma):
    pmin, pmax = get_pixel_range(img)
    # print("pixel range = {} to {}".format(pmin, pmax))
    # print("unique pixel count = {}".format(count_unique_pixels(img)))
    adjuster = ContrastAdjuster(pmin, pmax, gamma, (2 ** colorDepth) - 1)
    # vectorize to apply adjuster.adjust() to every pixel in img
    adjust_func = numpy.vectorize(adjuster.adjust)
    adj_img = adjust_func(img)
    return adj_img.astype('uint16') # adjust_func yields int64 array, convert to uint16

def load_ruler_image(rulerPath, colorDepth):
    ruler_img = cv2.imread(rulerPath, -1) # -1 to preserve file's color depth
    rulerDepth = get_color_depth(ruler_img)
    if colorDepth is None:
        raise UnexpectedColorDepthError("Ruler image {} has an unrecognized color depth. Only 16-bit and 8-bit are accepted.".format(rulerPath))

    rulerComponents = get_component_count(ruler_img)
    if rulerComponents == 3: # convert RGB to grayscale
        ruler_img = cv2.cvtColor(ruler_img, cv2.COLOR_BGR2GRAY)
    elif rulerComponents != 1:
        raise UnexpectedComponentCountError("Ruler image {} has an unexpected number of color components ({}). Only RGB and grayscale are accepted.".format(rulerPath, rulerComponents))
    # 5/10/2019 no need to convert to RGB as we require grayscale input and always output in grayscale
    # if rulerComponents == 1: # grayscale
    #     print("Converting grayscale ruler to RGB")
    #     ruler_img = grayscale_to_rgb(ruler_img)

    if rulerDepth == 8 and colorDepth == 16:
        print("Converting 8-bit ruler to 16-bit to match core image")
        # ruler_img *= 256 alone doesn't work, must explicitly change array dtype
        # from uint8 to uint16 first
        ruler_img = ruler_img.astype('uint16')
        ruler_img *= 256
    elif rulerDepth == 16 and colorDepth == 8:
        print("Converting 16-bit ruler to 8-bit to match core image")
        ruler8bit_img = ruler_img * 1/256.0 # float for Python 2, where 1/256 = 0
        ruler_img = ruler8bit_img.astype('uint8')
    return ruler_img


# rotate, adjust contrast, add ruler, save to destDir
def prepare_xrf(imgPath, rulerPath, gamma, outputBaseName, destDir):
    baseProgStr = "Processing {}...".format(imgPath)
    reportProgress(0, baseProgStr)
    radiographDir = 'radiograph'
    create_dirs(destDir, [radiographDir])

    img = cv2.imread(imgPath, -1)
    img = numpy.rot90(img, k=2) # rotate 180 degrees so core top is at image left
    imgWidth = img.shape[1]
    colorDepth = get_color_depth(img)
    component_count = get_component_count(img)
    if component_count == 3:
        raise UnexpectedComponentCountError("Image {} appears to be RGB. Only grayscale images are accepted.".format(imgPath))
    elif component_count != 1:
        raise UnexpectedComponentCountError("Image {} has an unexpected number of color components ({}). Only grayscale images are accepted.".format(imgPath, component_count))
    ruler_img = load_ruler_image(rulerPath, colorDepth)
    rulerWidth = ruler_img.shape[1]
    if rulerWidth < imgWidth:
        raise RulerTooShortError("Ruler image {} is too short for core image {}".format(rulerPath, imgPath))

    reportProgress(25, baseProgStr + "adjusting levels")
    adj_img = adjust_contrast(img, colorDepth, gamma)
    # print("adjusted image shape = {}, dtype = {}".format(adj_img.shape, adj_img.dtype))
    # print("adj_img = {}".format(adj_img))

    # Trim end of ruler so its width matches trimmed core image width, then
    # add to bottom of core image. Image widths must be the same to stack vertically
    # with numpy.concatenate().
    ruler_img = numpy.delete(ruler_img, range(imgWidth, rulerWidth), axis=1)
    tiff_img = numpy.concatenate((adj_img, ruler_img), axis=0)

    cv2.imwrite(os.path.join(destDir, radiographDir, outputBaseName + ".tif"), tiff_img)


if __name__ == "__main__":
    for rg in ["DNA-MUB17-1A-2L-1_XR", "DNA-MUB17-1A-3L-1_XR", "DNA-MUB17-1A-4L-1_XR"]:
        prepare_xrf("../data/ImageProcessing/XRF Images/{}/radiograph.tif".format(rg), "rulers/Geotek20ppmmRulerGrayscale_XRF.tif", 1.4, "{}_16bit".format(rg), "testdata")