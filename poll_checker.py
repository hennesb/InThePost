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


''' This module is responsible for disabling/enabling facebook wall polling. It loops through all users, for each user if
    they have accessed the application within the last month we will continue polling. If not polling will be disabled.
    We will use the audit table to determine the last access time and take that away from systime.now().
 
 '''

