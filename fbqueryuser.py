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
import fbtokenutil

class User(db.Model):
  """Our applications user object"""
  displayName = db.StringProperty()
  facebook_id = db.StringProperty()
  last_login = db.DateTimeProperty(auto_now_add=True)
  immediate_token = db.StringProperty()
  long_lived_token = db.StringProperty()
  last_poll_time = db.IntegerProperty()
  date_account_created = db.DateTimeProperty(auto_now_add=True)



def getFbUserDetails(access_token):
    whoIsthisUrl = "https://graph.facebook.com/me?access_token="+access_token
    userData = urlfetch.fetch(whoIsthisUrl)
    out_json = json.loads(userData.content)
    fbUser = out_json['id']
    fbName = out_json['name']
    logging.info("Logged in as " + fbName)
    return fbUser,fbName

def getUserFullName(userId, access_token):
    whoIsthisUrl = "https://graph.facebook.com/"+ userId +"?access_token="+access_token
    userData = urlfetch.fetch(whoIsthisUrl)
    out_json = json.loads(userData.content)
    fbUser = out_json['id']
    fbName = out_json['name']
    logging.info("Logged in as " + fbName)
    return fbName


def gen_parent_users_key(users=None):
  return db.Key.from_path('Users',users) 


def doesUserExist(facebook_id): 
   users = db.GqlQuery("SELECT * FROM User "
                      "WHERE ANCESTOR IS :1 AND facebook_id =:2",
                      gen_parent_users_key('Users'),
                      facebook_id)    
   logging.info("Count " + str(users.count()))
   logging.info("User type" + str(type(users)))
   return users.count()



def addUserToDataStore(token):
   fbUser,fbName=getFbUserDetails(token)
   sixty_day_token=fbtokenutil.genLongLivedAccessTokenSingleParam(token)
   users = db.GqlQuery("SELECT * FROM User WHERE facebook_id =:1",fbUser)
   if (users.count()==0):
     User(displayName=fbName,facebook_id=fbUser,immediate_token=token,long_lived_token=sixty_day_token).put()
   else:
     for user in users:
       user.immediate_token=token
       user.long_lived_token=sixty_day_token
       user.put()


def queryUserFromDataStore(fbUser):
   users = db.GqlQuery("SELECT * FROM User WHERE facebook_id =:1",fbUser)
   if (users.count() > 0):
     for user in users:
       return user



def myfriends_are(fbUser):
    user = queryUserFromDataStore(fbUser)
    access_token = user.long_lived_token
    logging.info("Long Lived token" + access_token)
    url = "https://graph.facebook.com/"+ fbUser + "/friends?access_token=" + access_token
    data = urlfetch.fetch(url)
    json_data = json.loads(data.content)
    return json_data



def getAllUsers():
    users = db.GqlQuery("SELECT * FROM User")    
    return users

def user_is_real_person(fb_id, access_token):
    try:
        url = "https://graph.facebook.com/"+ fb_id
        data = urlfetch.fetch(url)
        json_data = json.loads(data.content)
        if 'category' in json_data:
            logging.info("-- user_is_real_person --is COMPANY " + fb_id + " belonging to " + json_data['name'])
            return 0
        else:
            logging.info("-- user_is_real_person -- is REAL user " + fb_id)
            return 1
    except:
        return 1



def is_a_real_person(from_user):
    if 'category' in from_user:
        return 0
    else:
        return 1
     

  
