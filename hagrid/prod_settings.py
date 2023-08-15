from settings import *

DEBUG = False

with open("~/.django-secret") as f:
    SECRET_KEY = f.read().strip()

ALLOWED_HOSTS = ["c3foc.net"]

SITE_URL = "https://c3foc.net"

MEDIA_ROOT = "/var/hagrid/media/"
STATIC_ROOT = "/var/hagrid/static/"
