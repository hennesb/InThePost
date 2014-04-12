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


def genLongLivedAccessToken(user,existing_access_token):
  url1 = "https://graph.facebook.com/oauth/access_token?"
  url2 = "client_id=368589609876475&client_secret=9610ada038dcf5cf1d83fe3da31906bd&grant_type=fb_exchange_token&fb_exchange_token="+existing_access_token
  url = url1 + url2
  result = urlfetch.fetch(url)
  regex =re.compile('access_token=(.*?)&expires=')
  m=regex.search(result.content)
  long_lived_token = m.group(1)
  logging.info("Long lived token "+ long_lived_token)
  memcache.add(user+"long_lived",long_lived_token)
  return long_lived_token

def genLongLivedAccessTokenSingleParam(existing_access_token):
  url1 = "https://graph.facebook.com/oauth/access_token?"
  url2 = "client_id=368589609876475&client_secret=9610ada038dcf5cf1d83fe3da31906bd&grant_type=fb_exchange_token&fb_exchange_token="+existing_access_token
  url = url1 + url2
  result = urlfetch.fetch(url)
  regex =re.compile('access_token=(.*?)&expires=')
  m=regex.search(result.content)
  long_lived_token = m.group(1)
  logging.info("Long lived token "+ long_lived_token)
  return long_lived_token
