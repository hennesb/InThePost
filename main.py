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


def cacheComments(data,user):
    key = user + "_" + "comments"
    logging.info("Cache key" + key)
    memcache.add(key, data , time=300)

def getCacheComments(user):
    key = user + "_" + "comments"
    return memcache.get(key)


def gen_search_results_key(fb_user):
    return fb_user + "search_result_key"

def cache_results_of_last_search(key , last_result):
    memcache.add(key, last_result , time=300)

def delete_results_of_last_search(key):
    memcache.delete(key)

def convertFacebookDateTimeToPrintableDate(fb_date_time):
    f_date = fb_date_time[0:10]
    display_dt = datetime.datetime.strptime(f_date, "%Y-%m-%d").strftime("%d/%m/%Y")
    return display_dt

def generateFormToken(access_token , userName):
    token = hashlib.md5(access_token + userName).hexdigest()
    return token
    
def do_async_call_to_cache_wall(accessToken ,user ,name , since):
    logging.info("Invocation async task")
    url = "https://graph.facebook.com/"+ user +"/home?access_token="+accessToken +"&limit=50"
    logging.info("Url 1 is " + url)
    fbUserWallContent = urlfetch.fetch(url,deadline=20,headers = { 'Cache-Control': 'no-cache,max-age=0', 'Pragma': 'no-cache' })
    jsonData = json.loads(fbUserWallContent.content)
    
    if 'data' not in jsonData:
        logging.info("No data found in call for " + user  + "/" + name + " using token " + accessToken)
        return

    data = jsonData['data']
    fbmessages.processGraphApiJsonMessage(user ,name ,data, accessToken)
    allData = []
 
    # Only retrieve this data if the user is new
    if (fbqueryuser.doesUserExist(user)):
        while 1:
          if 'paging' in jsonData:
              paging=jsonData['paging']
              next = paging['next'] 
              logging.info(next)
              url=next
              fbUserWallContent = urlfetch.fetch(url,deadline=20,headers = { 'Cache-Control': 'no-cache,max-age=0', 'Pragma': 'no-cache' })
              jsonData = json.loads(fbUserWallContent.content)
              data = jsonData['data']
              fbmessages.processGraphApiJsonMessage(user ,name ,data)
              if len(data) > 0:
                  allData = allData + data
                  logging.info("Data " + str(len(data)) + " all data " + str(len(allData)))
          else:
              logging.info(json.dumps(jsonData,sort_keys=True, indent=4))
              break




class MainPage(webapp2.RequestHandler):

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


    def get(self):
        self.redirect("https://www.facebook.com/dialog/oauth?client_id=368589609876475&scope=read_stream&redirect_uri=https://myfacebookwallsearch.appspot.com/init")

    def post(self):
        logging.info('In HTTP POST method of main page')
        signed_request = self.request.get('signed_request')
        signature,data = signed_request.split('.')
        data += "=" * (len(data) - 4)
        logging.info('Signed Request ' + signed_request)
        if (signed_request is not None and signed_request is not ''):
          logging.info('Signed request populated. About to base64 decode it')
          base_decoded_data = base64.b64decode(data)
          logging.info('Base 64 decoded in facebook embedded app' + base_decoded_data)
          jsondata=json.loads(base_decoded_data)
          logging.info(jsondata)
          
          if 'oauth_token' in jsondata:
            logging.info("Request coming in from apps.facebook")
            session = get_current_session()
            last_search_term = ''
            if ('last_search_term' in session):
                last_search_term = session['last_search_term']
            
            access_token = jsondata['oauth_token']
            logging.info('OAuth token' + jsondata['oauth_token'])
            fbUser, fbName = fbqueryuser.getFbUserDetails(jsondata['oauth_token'])
            session['user'] = fbUser
            session['name'] = fbName
            fbqueryuser.addUserToDataStore(jsondata['oauth_token'])
            token = generateFormToken(access_token, fbUser)
            device = self.determine_device()
            audit.add_audit_record(fbUser,fbName,'fb_canvas_login_page', self.request.remote_addr, device)
            min_date, max_date = fbmessages.find_min_max_post_dates(fbUser)
            memcache.add(token, access_token)
            template_values = {
              'token': token,
              'userFullName' : fbName,
              'minDate' : min_date.strftime("%d-%m-%Y"),
              'maxDate' : max_date.strftime("%d-%m-%Y"),
              'last_search_term' : last_search_term
             }
	    #template = jinja_environment.get_template('indexfb.html')
            template = jinja_environment.get_template('new_home.html')
            self.response.out.write(template.render(template_values))
          else:
            login_url="https://www.facebook.com/dialog/oauth?client_id=368589609876475&scope=read_stream&redirect_uri=https://apps.facebook.com/srchfeeds/"
            self.response.out.write("<script> top.location.href='" + login_url +"'</script>")


            


class OAuthTokenProcessor(webapp2.RequestHandler):

    def getUsersIdAndFullNameByAccessToken(self,access_token):
       whoIsthisUrl = "https://graph.facebook.com/me?access_token="+access_token
       userData = urlfetch.fetch(whoIsthisUrl)
       out_json = json.loads(userData.content)
       fbUser = out_json['id']
       fbName = out_json['name']
       return fbUser,fbName

    def getAccessToken(self,code):
       url1="https://graph.facebook.com/oauth/access_token?client_id=368589609876475&redirect_uri=https://myfacebookwallsearch.appspot.com/init&"
       url2="client_secret=9610ada038dcf5cf1d83fe3da31906bd&code="
       url = url1 + url2 + code
       result = urlfetch.fetch(url)
       logging.info('Url fetched ')
       logging.info(result.content)
       regex =re.compile('access_token=(.*?)&expires=')
       m=regex.search(result.content)
       access_token = m.group(1)
       return access_token


# Http Processing below   

    def is_mobile_request(self):
        if "Mobile" in self.request.headers["User-Agent"]:
            return 1
        else:
            return 0

    def determine_device(self):
        if (self.is_mobile_request()):
            logging.info("Audit returning is mobile")
            return 'Mobile'
        else:
            logging.info("Audit returning is non-mobile")
            return 'Non-Mobile'

    def get(self):
        session = get_current_session()
        session['last_search_results'] = ''
        last_search_term = ''

        if ('last_search_term' in session):
            last_search_term = session['last_search_term']

        code = self.request.get('code')
        token = self.request.get('token')
        logging.info('Token in get request '+ token)
        logging.info(code)
        access_code = ''
	if (len(code) < 1):
          self.redirect("https://www.facebook.com/dialog/oauth?client_id=368589609876475&scope=read_stream&redirect_uri=https://myfacebookwallsearch.appspot.com/init")
	
        #access_token=self.getAccessToken(code) 
        #session['access_token'] = access_token
        if ('access_token' in session):
           access_token = session['access_token']
           logging.info("Access token in session :" + access_token)
        else:
           access_token = self.getAccessToken(code)  
           session['access_token'] = access_token
 
        fbUser, fbName = self.getUsersIdAndFullNameByAccessToken(access_token)
        device = self.determine_device()
        audit.add_audit_record(fbUser,fbName,'web_login_page', self.request.remote_addr, device)
        session['user']=fbUser
        session['name']=fbName

        logging.info("Added user to session")
        fbqueryuser.addUserToDataStore(access_token)
        min_date, max_date = fbmessages.find_min_max_post_dates(fbUser)
        logging.info('Yes ... User added to the database')
        token = generateFormToken(access_token, fbUser)
        memcache.add(token, access_token)

        template_values = {
            'token': token,
            'userFullName' : fbName,
            'minDate' : min_date.strftime("%d-%m-%Y"),
            'maxDate' : max_date.strftime("%d-%m-%Y"),
            'last_search_term' : last_search_term
        }
	#template = jinja_environment.get_template('indexfb.html')
        if self.determine_device() == 'Mobile':
            template = jinja_environment.get_template('app.html')
        else:
            template = jinja_environment.get_template('new_home.html')
        deferred.defer(do_async_call_to_cache_wall, access_token ,fbUser ,fbName , 0)
        #logging.info("Async call made")
        self.response.out.write(template.render(template_values))

    def post(self):
        session = get_current_session()
        signed_request = self.request.get('signed_request')
        logging.info('Signed Request ' + signed_request)

        if (signed_request is not None and signed_request is not ''):
          logging.info('Signed request populated. About to base64 decode it')
          base_encoded_data = base64.b64decode(signed_request)
          logging.info(base_encoded_data)
          self.response.out.write('Base 64 decoded ' + base_encoded_data)
        else:
          session['last_search_results'] = ''
          search_terms = self.request.get('search_terms')
          session['last_search_term'] = search_terms
          logging.info(search_terms)
          max_posts = self.request.get('max_posts')
          logging.info(max_posts)
          token = self.request.get('token')
          logging.info(token)
          accessToken = memcache.get(token)      
          fbUser, fbName = self.getUsersIdAndFullNameByAccessToken(accessToken)
          device = self.determine_device()
          audit.add_audit_record(fbUser,fbName,'search_page', self.request.remote_addr, device)
          long_lived_token = fbtokenutil.genLongLivedAccessToken(fbUser,accessToken)
          logging.info("about to call a search ")
          #delete_results_of_last_search(gen_search_results_key(fbUser))
          posts_matching_search = fbmessages.find_search_term(search_terms ,fbUser, self.is_mobile_request())
          jsonResults = {}
          lst = fbmessages.to_serializable_list(posts_matching_search)
          if (len(lst) < 1):
              session['last_search_term'] = ''
          #cache_results_of_last_search(gen_search_results_key(fbUser),lst)
          jsonResults['matchingResults'] = lst
          listToJson = json.dumps(jsonResults);
          session['last_search_results'] = listToJson
          logging.info("Last search entry added to session")
          self.response.out.write(listToJson)
             
 

app = webapp2.WSGIApplication([('/', MainPage),('/init',OAuthTokenProcessor),('/realtime',realtimecallback.RealTimeMessageProcessor)],
                              debug=True)
