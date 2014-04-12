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

class MobileApp(webapp2.RequestHandler):

    def is_mobile_request(self):
        if "Mobile" in self.request.headers["User-Agent"]:
            return 1
        else:
            return 0


    def determine_device(self):
        if self.is_mobile_request():
            return 'Mobile'
        else:
            return 'Non-Mobile'

    def handle_no_results_found(self,lst):
        if len(lst) > 0:
            return lst
        else:
            new_lst = []
            data = {'from_user': 'No results found', 'post_link' : '#', 'created_time' : ' '}
            new_lst.append(data)
            return new_lst


    def get(self):
        device = self.determine_device()
        search_term = self.request.get('searchbox')
        access_token, fb_user, fb_name = self.pull_data_from_session()
        audit.add_audit_record(fb_user,fb_name,'search_page', self.request.remote_addr, device)
        long_lived_token = fbtokenutil.genLongLivedAccessToken(fb_user,access_token)
        posts_matching_search = fbmessages.find_search_term(search_term ,fb_user, self.is_mobile_request())
        results = fbmessages.to_serializable_list(posts_matching_search)
        min_date, max_date = fbmessages.find_min_max_post_dates(fb_user)                
        template_values = {'last_search_term': search_term, 
                           'results': self.handle_no_results_found(results),
                           'minDate': min_date.strftime("%d-%m-%Y"),
                           'maxDate': max_date.strftime("%d-%m-%Y") }
        template = jinja_environment.get_template('app.html')
        self.response.out.write(template.render(template_values))

    def post(self):
        logging.info("In post method")


    def pull_data_from_session(self):
        session = get_current_session()
        access_token = ""
        fb_user = ""
        fb_name =""

        if 'access_token' in session:
            logging.info('Acccess token is in session')
            access_token = session['access_token']
        else:
            logging.info('no acccess token is in session')
            raise Exception('Security issue detected')

        if 'user' in session:
            logging.info('user is in session')
            fb_user = session['user']
        else:
            logging.info('no user is in session')
            raise Exception('Security issue detected')

        if 'name' in session:
            logging.info('name is in session')
            fb_name = session['name']
        else:
            logging.info('no name is in session')
            raise Exception('Security issue detected')
        return access_token,fb_user,fb_name



app = webapp2.WSGIApplication([('/mobileApp', MobileApp)],
                              debug=True)
