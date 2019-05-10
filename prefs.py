# Get/set/read/write preference data to/from a Python pickle file

import logging
import os
import pickle

logger = logging.getLogger(__name__)

class Preferences:
    # prefPath - path to preferences pickle file to be used, which will
    # be created if it doesn't exist. Assumes parent directory already
    # exists.
    def __init__(self, prefPath):
        self.prefPath = prefPath

        self.prefmap = {}
        self.read()

    def write(self):
        with open(self.prefPath, 'wb') as pf:
            pickle.dump(self.prefmap, pf)
            pf.close()
            logger.info("saved preferences: " + str(self.prefmap))

    def read(self):
        if os.path.exists(self.prefPath):
            pf = open(self.prefPath, 'rb')
            self.prefmap = pickle.load(pf)
            pf.close()
            logger.info("loaded prefs: " + str(self.prefmap))
        else:
            logger.info("no prefs found at " + self.prefPath)

    def contains(self, key):
        return key in self.prefmap

    def get(self, key, default=""):
        return self.prefmap[key] if key in self.prefmap else default
    
    def set(self, key, value):
        self.prefmap[key] = value
