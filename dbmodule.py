import re
import json
import os
import hashlib
import logging
import base64
import urllib
import datetime
import time
from google.appengine.ext import db


class Posts(db.Model):
  post_url = db.LinkProperty()
  post_datetime = db.DateTimeProperty()
  post_contents = db.StringListProperty()
  comment_url = db.LinkProperty()
  user_id = db.StringProperty()


