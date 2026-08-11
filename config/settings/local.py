from .base import *

# Local Development Database
DATABASES = {
    'default': env.db('DATABASE_URL', default='postgres://postgres:postgres@localhost:5432/studenterp1')
}
