# LacCore/CSDCO
# geotek.py
#
# Prepare a raw vertically-oriented Geotek core scanner TIFF image
# for use by doing the following:
# 1. Rotate image 90 degrees CCW, so core top is on the left
# 2. Based on provided DPI, chop off the left .25 inches of the image
# by default - chop amount can be customized.
# 3. Add ruler image (with same DPI as input image) below core image.
# 4. Save resulting image in TIFF and JPEG formats, writing to tiff
# and jpeg dirs created in application root directory.
# 5. Create ICD-sized version of the image by rotating 90 CW so core
# top is on top, downscaling image to 30% (default, can be customized),
# and writing JPEG to ICD dir created in application root directory.
# 6. Output images' names are based on input image's parent directory
# name, with format-appropriate extension added e.g. /coreimage/img1.tif
# would yield [app root]/tiff/coreimage.tif, [app root]/jpeg/coreimage.jpg,
# and [app root]/ICD/coreimage.jpg

import os
import numpy as np
import cv2 # OpenCV

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


# imgPath - full path to input Geotek image
# rulerPath - full path to input ruler image - must be in RGB (see Note above)
# trim - amount, in inches, to trim from core top
# dpi - resolution of input image and ruler
# icdScaling - percentage to which ICD image should be scaled
# outputBaseName - filename (without extension) to use for outputs - format-appropriate extension will be added
# destDir - directory in which jpeg, tiff, and ICD dirs will be created,
# to which image outputs will be written
def prepare_geotek(imgPath, rulerPath, dpi, trim, icdScaling, outputBaseName, destPath):
    baseProgStr = "Processing {}...".format(imgPath)
    reportProgress(0, baseProgStr)
    TiffDir, JpegDir, IcdDir = 'tiff', 'jpeg', 'ICD'
    create_dirs(destPath, [TiffDir, JpegDir, IcdDir])

    img = cv2.imread(imgPath, -1) # -1 to preserve file's color depth e.g. 16-bit
    print("Image depth: {}".format(img.dtype))
    wid, hit = img.shape[:2]

    # Rotate image 90deg counter-clockwise so core top is at image left
    reportProgress(10, baseProgStr + "rotating")
    adj_img = np.rot90(img)

    # Trim [trim] inches from core top (now the left side of image)
    reportProgress(30, baseProgStr + "trimming {} inches from core top".format(trim))
    chopWidth = round(dpi * trim)
    # print("chopWidth = {} pixels".format(chopWidth))
    chop_img = np.delete(adj_img, range(0, chopWidth), axis=1)

    # Load ruler file
    reportProgress(60, baseProgStr + "adding ruler")
    ruler_img = cv2.imread(rulerPath, -1)
    print("Ruler image depth: {}".format(ruler_img.dtype))
    rh, rw = ruler_img.shape[:2]

    # Trim end of ruler so its width matches trimmed core image width, then
    # add to bottom of core image. Image widths must be the same to stack vertically
    # with numpy.concatenate().
    ruler_img = np.delete(ruler_img, range(wid - chopWidth, rw), axis=1)
    rhit, rwid = ruler_img.shape[:2]
    dest_img = np.concatenate((chop_img, ruler_img), axis=0)

    # Save as TIFF to tiff subdir
    reportProgress(70, baseProgStr + "writing TIFF")
    cv2.imwrite(os.path.join(destPath, TiffDir, outputBaseName + ".tif"), dest_img)

    # Save as JPEG to jpeg subdir
    reportProgress(80, baseProgStr + "writing JPEG")
    rgb8bit_img = dest_img * 0.00390625 # scale 16-bit values to 8-bit by multiplying by 1/256
    cv2.imwrite(os.path.join(destPath, JpegDir, outputBaseName + ".jpg"), rgb8bit_img)

    # For ICD image, rotate back to vertical (core top at image top),
    # resize by [icdScaling] percentage and write as JPEG in ICD subdir
    reportProgress(90, baseProgStr + "writing ICD JPEG")
    icd_img = np.rot90(rgb8bit_img, axes=(1,0))
    icdhit, icdwid = icd_img.shape[:2]
    scaling = icdScaling/100.0
    scaled_dims = (int(round(icdwid * scaling)), int(round(icdhit * scaling)))
    icd_img = cv2.resize(icd_img, scaled_dims, interpolation=cv2.INTER_AREA)
    cv2.imwrite(os.path.join(destPath, IcdDir, outputBaseName + ".jpg"), icd_img)


if __name__ == "__main__":
    rulerPath = 'rulers/Geotek20ppmmRuler16bitRGB.tif'
    # prepare_geotek('testdata/OGDP-OLD14-2A-15Y-1-A.tif', rulerPath=None, dpi=508, trim=0.25, icdScaling=25, outputBaseName="OGDP-OLD14-2A-15Y-1-A", destPath='testdata')
    prepare_geotek('testdata/stubby.tif', rulerPath, dpi=508, trim=0.25, icdScaling=25, outputBaseName="stubby", destPath='testdata')