import webapp2
from google.appengine.api import urlfetch
import re
import json
import jinja2
import os
import hashlib
from google.appengine.api import memcache
import logging
import base64
import urllib
import datetime
import time
from google.appengine.ext import deferred
from google.appengine.ext import db
import realtimecallback
import fbqueryuser
import fbtokenutil
import fbmessages
from datetime import datetime
from time import strptime
from gaesessions import get_current_session
import audit

jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)))


class PrivacyPage(webapp2.RequestHandler):

    def get(self):
            template = jinja_environment.get_template('privacy.html')
            self.response.out.write(template.render())

app = webapp2.WSGIApplication([('/privacy', PrivacyPage)],
                              debug=True)
