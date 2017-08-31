from config.base import *

# This config is configured for running local tests
TESTING = True
DEBUG = True

# Use in-memory SQLlite DB for testing
SQLALCHEMY_DATABASE_URI = 'sqlite:///database/jobs.db'
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Load cases from resources json file
LOAD_CASES = False
LOAD_DEVELOPMENT_CASES = True
