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
import fbqueryuser
import fbmessages


class RealTimeMessageProcessor(webapp2.RequestHandler):

  def getToken(self):
    url = "https://graph.facebook.com/oauth/access_token?client_id=XXXXXXX&client_secret=XXXXXXX&grant_type=client_credentials"
    body = urlfetch.fetch(url,deadline=20,headers = { 'Cache-Control': 'no-cache,max-age=0', 'Pragma': 'no-cache' })
    content = body.content
    eq_sign = content.find('=')
    token= content[eq_sign+1:]
    logging.info("Token is " + token)
    return token
  

  def get(self):
    logging.info("This is the real time update get method being invoked")
    hubMode = self.request.get('hub.mode')
    hubChallenge = self.request.get('hub.challenge')
    hubToken = self.request.get('hub.verify_token')
    logging.info("Hub Mode " + hubMode)
    logging.info("Hub Challenge " + hubChallenge)
    logging.info("Hub token " + hubToken)

    if (hubToken=='inthepost9999'):
      self.response.out.write(hubChallenge)
         

  def post(self):
    access_token = self.getToken()
    logging.info("This is the real time update post method being invoked")
    messageBody = self.request.body
    jsonData = json.loads(messageBody)
    logging.info(json.dumps(jsonData,sort_keys=True, indent=4))
    data = jsonData['entry']
    for i in data:
      fbUser = i['id']
      who = fbqueryuser.getUserFullName(fbUser, access_token)
      logging.info("Whose wall changed " + who)
      #token = memcache.get(user+"long_lived")
      user = fbqueryuser.queryUserFromDataStore(fbUser)
      token = None
      if user is not None:
        token=user.long_lived_token
  

      if (token is not None):
        thisUsersWallUrl = "https://graph.facebook.com/"+ fbUser +"/home?access_token="+token+"&limit=99"
        logging.info(thisUsersWallUrl)
        fbUserWallContent = urlfetch.fetch(thisUsersWallUrl,deadline=20,headers = { 'Cache-Control': 'no-cache,max-age=0', 'Pragma': 'no-cache' })
        wallData = json.loads(fbUserWallContent.content) 
        if 'data' in wallData:
            data = wallData['data']
            fbmessages.processGraphApiJsonMessage(fbUser ,who ,data, token)  
        #logging.info(json.dumps(wallData,sort_keys=True, indent=4)) 
      else:
        logging.info("User " + who + " does not have a long lived token")   
