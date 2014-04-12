import webapp2
from google.appengine.api import urlfetch
import re
import json
import os
import hashlib
from google.appengine.api import memcache
import logging
import base64
import urllib
import datetime
import time
from google.appengine.ext import db


class Audit(db.Model):
    facebook_id = db.StringProperty()
    name = db.StringProperty()
    access_time = db.DateTimeProperty(auto_now_add=True)
    screen = db.StringProperty()
    ip_address = db.StringProperty()
    device_type = db.StringProperty()


def gen_parent_audit_key(audit=None):
    return db.Key.from_path('Audit',audit)

def add_audit_record(facebook_id, name, screen, ip_address, device):
    audit = Audit(gen_parent_audit_key('Audit'))
    audit.facebook_id = facebook_id
    audit.name = name
    audit.screen = screen
    audit.ip_address = ip_address
    audit.device_type = device
    audit.put()






