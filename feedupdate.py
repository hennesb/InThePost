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
import fbmessages
import fbqueryuser



def get_users_feed(user):
    logging.info(str(type(user)))
    fbUser = user.facebook_id
    last_poll_time = user.last_poll_time
    access_token = user.long_lived_token
    logging.info("Getting the cron wall feed for " + fbUser)
    thisUsersWallUrl = ""
    if (last_poll_time is None):
        thisUsersWallUrl = "https://graph.facebook.com/"+ fbUser +"/home?access_token=" + access_token + "&limit=99"
    else:
        thisUsersWallUrl = "https://graph.facebook.com/"+ fbUser +"/home?access_token=" + access_token + "&limit=99"
        logging.info(thisUsersWallUrl)
        
    fbUserWallContent = urlfetch.fetch(thisUsersWallUrl,deadline=100,headers = { 'Cache-Control': 'no-cache,max-age=0', 'Pragma': 'no-cache' })
    now = int(time.time())
    user.last_poll_time = now
    user.put()
    wallData = json.loads(fbUserWallContent.content) 
    if 'data' in wallData:
        data = wallData['data']
        deferred.defer(fbmessages.processGraphApiJsonMessage ,fbUser , user.displayName, data , access_token)
        

def process_users():
    users = fbqueryuser.getAllUsers()
    return filter(lambda x:get_users_feed(x), users)


class FBBatchUserWallFeedProcessor(webapp2.RequestHandler):
    def get(self):
        process_users()

app = webapp2.WSGIApplication([('/fbuserfeedupdate', FBBatchUserWallFeedProcessor)],
                              debug=True)
