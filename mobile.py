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

jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)))



class Mobile(webapp2.RequestHandler):
    def get(self):
        template_values = {}
        template = jinja_environment.get_template('mobile.html')
        self.response.out.write(template.render(template_values))


app = webapp2.WSGIApplication([('/mobile',Mobile)],
                              debug=True)
