# CSD Facility
# geotek_opencv.py
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


import os
import numpy as np
import cv2 # OpenCV

from common import create_dirs, UnexpectedColorDepthError, RulerTooShortError, get_component_count, get_color_depth, grayscale_to_rgb, remove_alpha_channel

ProgressListener = None

def setProgressListener(pl):
    global ProgressListener
    ProgressListener = pl
    ProgressListener.clear()

def reportProgress(value, text):
    global ProgressListener
    if ProgressListener:
        ProgressListener.setValueAndText(value, text)

# Load ruler image file at rulerPath, convert grayscale to
# RGB color, adjust depth to match colorDepth.
def load_ruler_image(rulerPath, colorDepth):
    ruler_img = cv2.imread(rulerPath, -1) # -1 to preserve file's color depth
    rulerComponents = get_component_count(ruler_img)
    rulerDepth = get_color_depth(ruler_img)
    if colorDepth is None:
        raise UnexpectedColorDepthError("Ruler image {} has an unrecognized color depth. Only 16-bit and 8-bit are accepted.".format(rulerPath))
    if rulerComponents == 1: # grayscale
        print("Converting grayscale ruler to RGB")
        ruler_img = grayscale_to_rgb(ruler_img)
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

# imgPath - full path to input Geotek image
# rulerPath - full path to input ruler image - must be in RGB (see Note above)
# dpi - resolution of input image and ruler
# trim - amount, in inches, to trim from core top
# icdScaling - percentage to which ICD image should be scaled
# outputBaseName - filename (without extension) to use for outputs - format-appropriate extension will be added
# destPath - directory in which jpeg, tiff, and ICD dirs will be created,
# to which image outputs will be written
def prepare_geotek(imgPath, rulerPath, dpi, trim, icdScaling, outputBaseName, destPath):
    baseProgStr = "Processing {}...".format(imgPath)
    reportProgress(0, baseProgStr)
    TiffDir, JpegDir, IcdDir = 'tiff', 'jpeg', 'ICD'
    create_dirs(destPath, [TiffDir, JpegDir, IcdDir])

    # Load core image
    img = cv2.imread(imgPath, -1) # -1 to preserve file's color depth
    print("Image depth: {}".format(img.dtype))
    colorDepth = get_color_depth(img)
    if colorDepth is None:
        raise UnexpectedColorDepthError("Image {} has an unrecognized color depth. Only 16-bit and 8-bit are accepted.".format(imgPath))
    imageWidth = img.shape[0] # this is img.height, but due to upcoming rotation height will be image width

    # Load ruler image and confirm it's long enough for core image
    ruler_img = load_ruler_image(rulerPath, colorDepth)
    rulerWidth = ruler_img.shape[1]
    if rulerWidth < imageWidth:
        raise RulerTooShortError("Ruler image {} is too short for core image {}".format(rulerPath, imgPath))

    # Remove alpha channel from core image and ruler image if needed
    if get_component_count(img) == 4:
        img = remove_alpha_channel(img)
    if get_component_count(ruler_img) == 4:
        ruler_img = remove_alpha_channel(ruler_img)

    # Rotate image 90deg counter-clockwise so core top is at image left
    reportProgress(10, baseProgStr + "rotating")
    adj_img = np.rot90(img)

    # Trim [trim] inches from core top (now the left side of image)
    reportProgress(30, baseProgStr + "trimming {} inches from core top".format(trim))
    chopWidth = round(dpi * trim)
    # print("chopWidth = {} pixels".format(chopWidth))
    chop_img = np.delete(adj_img, range(0, chopWidth), axis=1)

    # Trim end of ruler so its width matches trimmed core image width, then
    # add to bottom of core image. Image widths must be the same to stack vertically
    # with numpy.concatenate().
    reportProgress(60, baseProgStr + "adding ruler")
    ruler_img = np.delete(ruler_img, range(imageWidth - chopWidth, rulerWidth), axis=1)
    tiff_img = np.concatenate((chop_img, ruler_img), axis=0)

    # Save as TIFF to tiff subdir
    reportProgress(70, baseProgStr + "writing TIFF")
    cv2.imwrite(os.path.join(destPath, TiffDir, outputBaseName + ".tif"), tiff_img)

    # Save as JPEG to jpeg subdir, downscaling 16-bit to 8-bit if needed. JPEG
    # components must be 8-bit.
    reportProgress(80, baseProgStr + "writing JPEG")
    jpeg_img = tiff_img * 1/256.0 if colorDepth == 16 else tiff_img # float for Python 2, where 1/256 = 0
    cv2.imwrite(os.path.join(destPath, JpegDir, outputBaseName + ".jpg"), jpeg_img)

    # For ICD image, rotate back to vertical (core top at image top),
    # resize by [icdScaling] percentage and write as JPEG in ICD subdir
    reportProgress(90, baseProgStr + "writing ICD JPEG")
    icd_img = np.rot90(jpeg_img, axes=(1,0))
    icdhit, icdwid = icd_img.shape[:2]
    scaling = icdScaling/100.0
    scaled_dims = (int(round(icdwid * scaling)), int(round(icdhit * scaling)))
    icd_img = cv2.resize(icd_img, scaled_dims, interpolation=cv2.INTER_AREA)
    cv2.imwrite(os.path.join(destPath, IcdDir, outputBaseName + ".jpg"), icd_img)


if __name__ == "__main__":
    rulerFiles = ["16bitRGB", "8bitRGB", "16bitGrayscale", "8bitGrayscale"]
    for rf in rulerFiles:
        rulerPath = "rulers/Geotek20ppmmRuler{}.tif".format(rf)
        prepare_geotek('testdata/stubby8bit.tif', rulerPath, dpi=508, trim=0.25, icdScaling=25, outputBaseName="stubby8bit_{}".format(rf), destPath='testdata')