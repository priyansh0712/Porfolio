from .base import *

DEBUG = False

DATABASES = {
    'default': env.db('DATABASE_URL')
}
