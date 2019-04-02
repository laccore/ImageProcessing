# Logic common to Geotek and XRF conversion routines

import os, re, sys

# For each string in dirs, create a directory of that name
# beneath destDir if it doesn't exist already. Assumes that
# destDir already exists.
def create_dirs(destDir, dirs):
    for newdir in [os.path.join(destDir, d) for d in dirs]:
        mkdir_if_needed(newdir)

def mkdir_if_needed(newdir):
    if not os.path.exists(newdir):
        os.mkdir(newdir)

# Return path to directory containing .app bundle, .exe, or Python
# script launched from command line, handling awkward Mac OSX 
# pyinstaller-created .app bundle case
def get_app_path():
    # on Mac, we need to find the directory in which the .app bundle lives
    # but os.getcwd() returns the path to the internal binary i.e.
    # /.../[app root]/Contents/MacOS
    # 'frozen' attr indicates we're running in a pyinstaller-created app bundle
    if sys.platform == 'darwin' and getattr(sys, 'frozen', False):
        binaryPath = sys.executable
        # find instance of [AppName].app
        match = re.search(r"[A-Za-z0-9 \._-]+\.app", binaryPath)
        if match:
            return binaryPath[:match.start()] # trim everything beyond start of match
        else:
            # This should be unlikely since Apple makes it hard to rename a .app file:
            # .app is re-added if you attempt to remove it from the name in Finder.
            raise InvalidApplicationPathError("Couldn't find application directory.")
    else: # Windows .exe or command-line-invoked on Windows or Mac
        return os.getcwd()

class InvalidApplicationPathError(Exception):
    def __init__(self, message):
        super(InvalidApplicationPathError, self).__init__(message)
        self.message = message

class UnexpectedColorDepthError(Exception):
    def __init__(self, message):
        super(UnexpectedColorDepthError, self).__init__(message)
        self.message = message

class RulerTooShortError(Exception):
    def __init__(self, message):
        super(RulerTooShortError, self).__init__(message)
        self.message = message