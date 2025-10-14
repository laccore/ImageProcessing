# CSD Facility
# romacons.py
#
# Special-casing geotek_opencsv.py logic for "rolled" unsplit concrete core
# imaging. Each core will be scanned and rotated 3-4 times to capture
# the entire surface of the unsplit core. The resulting images will be vertically
# concatenated, and a ruler will be added. TIFF and JPEGs of the concatenated
# image will be created in the tiff and jpeg output dirs.
# For ICD, only the first image will be used. A ruler will be added, then the resulting
# image would be downscaled and output to the ICD directory as JPEG, just as we do
# in geotek_opencsv.py.
#
# Assumptions:
# - All images to be merged have *exactly* the same pixel count along the depth axis
# - The same top trim amount will be applied to all images
# - ICD image will include only the first core image, with ruler added


import os
import numpy as np
import cv2 # OpenCV

from common import create_dirs, UnexpectedColorDepthError, RulerTooShortError, get_component_count, get_color_depth, grayscale_to_rgb, remove_alpha_channel
from geotek_opencv import load_ruler_image

ProgressListener = None

def setProgressListener(pl):
    global ProgressListener
    ProgressListener = pl
    ProgressListener.clear()

def reportProgress(value, text):
    global ProgressListener
    if ProgressListener:
        ProgressListener.setValueAndText(value, text)


# coreImagePaths - list of full paths to Geotek images to be merged
# rulerPath - full path to input ruler image - must be in RGB (see Note above)
# dpi - resolution of input images and ruler
# trim - amount, in inches, to trim from the top of each image's top
# icdScaling - percentage of original to which ICD image should be scaled
# outputBaseName - filename (without extension) to use for outputs - format-appropriate extension will be added
# destPath - directory in which jpeg, tiff, and ICD dirs will be created,
# to which image outputs will be written
def prepare_romacons(coreImagePaths, rulerPath, dpi, trim, icdScaling, outputBaseName, destPath):
    baseProgStr = f"Merging {len(coreImagePaths)} rotated images..."
    reportProgress(0, baseProgStr)
    TiffDir, JpegDir, IcdDir = 'tiff', 'jpeg', 'ICD'
    create_dirs(destPath, [TiffDir, JpegDir, IcdDir])

    # Load core images
    reportProgress(10, baseProgStr + "loading image data")
    coreImages = [cv2.imread(imagePath, -1) for imagePath in coreImagePaths] # -1 to preserve file's color depth

    # Validate color depth
    reportProgress(20, baseProgStr + "validating image properties")
    allColorDepths = []
    for idx, ci in enumerate(coreImages):
        colorDepth = get_color_depth(ci)
        if colorDepth is None:
            raise UnexpectedColorDepthError("Image {} has an unrecognized color depth. Only 16-bit and 8-bit are accepted.".format(coreImagePaths[idx]))
        allColorDepths.append(colorDepth)

    # Confirm uniform color depths
    if len(set(allColorDepths)) != 1:
        raise Exception(f"Color depth of images is not uniform: {allColorDepths}")
    
    # Confirm uniform pixel counts along depth axis
    depthAxisPixelCounts = [ci.shape[0] for ci in coreImages] # depth axis is vertical in loaded image orientation
    if len(set(depthAxisPixelCounts)) != 1:
        raise Exception(f"Depth axis pixel count of images is not uniform: {depthAxisPixelCounts}")

    # Load ruler image and confirm it's long enough for core image
    reportProgress(30, baseProgStr + "loading ruler image")
    ruler_img = load_ruler_image(rulerPath, allColorDepths[0])
    rulerWidth = ruler_img.shape[1]
    if rulerWidth < depthAxisPixelCounts[0]:
        raise RulerTooShortError(f"Ruler image ({rulerWidth} pixels) is too short for core images ({depthAxisPixelCounts[0]} pixels)")

    # Remove alpha channel from core images and ruler image if needed
    alphaRemovedCoreImages = []
    for ci in coreImages:
        if get_component_count(ci) == 4:
            ci = remove_alpha_channel(ci)
        alphaRemovedCoreImages.append(ci)
    if get_component_count(ruler_img) == 4:
        ruler_img = remove_alpha_channel(ruler_img)

    # Rotate image 90deg counter-clockwise so core top is at image left
    reportProgress(40, baseProgStr + "rotating core images")
    rotatedCoreImages = []
    for ci in alphaRemovedCoreImages:
        ci = np.rot90(ci)
        rotatedCoreImages.append(ci)

    # Trim [trim] inches from core top (now the left side of image)
    chopWidth = round(dpi * trim)
    reportProgress(60, baseProgStr + f"trimming {trim} inches ({chopWidth} pixels) from core tops")
    # print("chopWidth = {} pixels".format(chopWidth))
    trimmedCoreImages = []
    for ci in rotatedCoreImages:
        ci = np.delete(ci, range(0, chopWidth), axis=1)
        trimmedCoreImages.append(ci)

    # Concatenate core images vertically
    reportProgress(70, baseProgStr + f"merging core images vertically")
    tiff_img = np.concatenate(tuple(tci for tci in trimmedCoreImages), axis=0)

    # Trim end of ruler so its width matches trimmed core image width, then
    # add to bottom of core image. Image widths must be the same to stack vertically
    # with numpy.concatenate().
    reportProgress(80, baseProgStr + "adding ruler")
    ruler_img = np.delete(ruler_img, range(depthAxisPixelCounts[0] - chopWidth, rulerWidth), axis=1)
    tiff_img = np.concatenate((tiff_img, ruler_img), axis=0)

    # Save as TIFF to tiff subdir
    reportProgress(85, baseProgStr + "writing TIFF")
    cv2.imwrite(os.path.join(destPath, TiffDir, outputBaseName + ".tif"), tiff_img)

    # Save as JPEG to jpeg subdir, downscaling 16-bit to 8-bit if needed. JPEG
    # components must be 8-bit.
    reportProgress(90, baseProgStr + "writing JPEG")
    # jpeg_img = tiff_img * 1/256.0 if colorDepth == 16 else tiff_img # float for Python 2, where 1/256 = 0
    jpeg_img = (tiff_img * 1/256).astype(np.uint8) if colorDepth == 16 else tiff_img
    cv2.imwrite(os.path.join(destPath, JpegDir, outputBaseName + ".jpg"), jpeg_img)

    # Create ICD image using first core image only
    icd_img = np.concatenate((trimmedCoreImages[0], ruler_img), axis=0)
    if colorDepth == 16:
        icd_img = (icd_img * 1/256).astype(np.uint8)

    # Rotate ICD image back to vertical (core top at image top),
    # resize by [icdScaling] percentage and write as JPEG in ICD subdir
    reportProgress(95, baseProgStr + "writing ICD JPEG")
    icd_img = np.rot90(icd_img, axes=(1,0))
    icdhit, icdwid = icd_img.shape[:2]
    scaling = icdScaling/100.0
    scaled_dims = (int(round(icdwid * scaling)), int(round(icdhit * scaling)))
    icd_img = cv2.resize(icd_img, scaled_dims, interpolation=cv2.INTER_AREA)
    cv2.imwrite(os.path.join(destPath, IcdDir, outputBaseName + ".jpg"), icd_img)


if __name__ == "__main__":
    coreImagePaths = [
        'ROMACONS/GUAC-1A-1G-1-W-rot1.tif',
        'ROMACONS/GUAC-1A-1G-1-W-rot2.tif',
        'ROMACONS/GUAC-1A-1G-1-W-rot3.tif',
        # 'ROMACONS/GUAC-1A-1G-1-W-rot4.tif',
    ]
    rulerPath = 'rulers/Geotek20ppmmRulerGrayscale.jpg'

    prepare_romacons(coreImagePaths, rulerPath, 508, 0.25, 30.0, 'merged', 'ROMACONS/outputs')