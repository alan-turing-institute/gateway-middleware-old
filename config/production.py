from config.base import *
# This config is configured for production

DEBUG = False

# Use in-memory SQLlite DB for now
# (will need to update to Azure specific sql/mysql URI
# once Azure webapp + SQL integration is implemented)
SQLALCHEMY_DATABASE_URI = 'sqlite://'

# Disable track modifications as we are not using
# the Flask-SQLAlchemy event system
SQLALCHEMY_TRACK_MODIFICATIONS = False

# The path to the cases file
cases_path = ('https://science-gate-way-middleware.azurewebstes.net/'
              'resources/cases/blue.json')
