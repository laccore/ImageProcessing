# Logic common to Geotek and XRF conversion routines

import os

# For each string in dirs, create a directory of that name
# beneath destDir if it doesn't exist already. Assumes that
# destDir already exists.
def create_dirs(destDir, dirs):
    for newdir in [os.path.join(destDir, d) for d in dirs]:
        mkdir_if_needed(newdir)

def mkdir_if_needed(newdir):
    if not os.path.exists(newdir):
        os.mkdir(newdir)
