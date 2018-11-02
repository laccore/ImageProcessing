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

    img = Image.open(imgPath)

    # Image.rotate() doesn't rotate the canvas/image bounds, only the
    # pixels themselves. Image.transpose() does both as expected.
    reportProgress(10, baseProgStr + "rotating")    
    adj_img = img.transpose(Image.ROTATE_90)

    # chop off .25 inches from core top (now the left side of image)
    chopWidth = round(dpi * trim)
    #print("chopWidth = {} pixels".format(chopWidth))
    reportProgress(30, baseProgStr + "cropping")    
    adj_img = adj_img.crop((chopWidth, 0, adj_img.width, adj_img.height))

    # add ruler
    reportProgress(60, baseProgStr + "adding ruler")
    ruler_img = Image.open(rulerPath)
    dest_img = Image.new("RGB", (adj_img.width, adj_img.height + ruler_img.height))
    dest_img.paste(adj_img)
    dest_img.paste(ruler_img, (0, adj_img.height))
    
    # save as TIFF to tiff subdir
    reportProgress(70, baseProgStr + "writing TIFF")
    dest_img.save(os.path.join(destPath, TiffDir, outputBaseName + ".tif"))

    # save as JPEG to jpeg subdir
    reportProgress(80, baseProgStr + "writing JPEG")
    dest_img.save(os.path.join(destPath, JpegDir, outputBaseName + ".jpg"))

    # for ICD image, rotate back to vertical (core top on top),
    # resize and write as JPEG in ICD subdir
    reportProgress(90, baseProgStr + "writing ICD JPEG")
    icd_img = dest_img.transpose(Image.ROTATE_270)
    scaling = icdScaling/100.0
    scaled_dims = (int(round(icd_img.width * scaling)), int(round(icd_img.height * scaling)))   
    icd_img = icd_img.resize(scaled_dims)
    icd_img.save(os.path.join(destPath, IcdDir, outputBaseName + ".jpg"))
