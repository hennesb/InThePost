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
import stopwords
from gaesessions import get_current_session
import collections
import random
import audit



class TagCloudPosts(webapp2.RequestHandler):


  def calc_font_size(self, count, max_freq):
      min_font_size = 10
      max_font_size = 70

      if (count==max_freq):
          return max_font_size

      if (count <= 2):
          return min_font_size

      font_size = (count / float(max_freq)) * (max_font_size - min_font_size) + min_font_size
      return font_size

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


  def generate_html(self, c):
      html= "<html>"
      header="<p class=\"fbbluebox\">This page is for fun and self reflection. See what the predominant words you use on facebook are</p>"
      div= "<div class=\"fbtagcloud\" style=\"WIDTH: 680px;overflow=\"auto\"\">"      
      end = "</div></html>"
      inner_html = ""
      tuple_list = []

      for t in c.most_common(75):  
          tuple_list.append(t)

      if (len(tuple_list) < 1):
          return "<span style=\"color:#0000A0;font-size:25px\" >No posts found for this user</span>"  

      first_element = tuple_list[0]
      max_freq = first_element[1]
      random.shuffle(tuple_list)  

      start_span = "<span style=\"color:#0000A0;font-size:"
      for r in tuple_list:
          if (r[1] > 1):
              inner_html= inner_html + start_span  + str(self.calc_font_size(r[1], max_freq)) + "px\">" + r[0] + "  " + "</span>"

      logging.info(inner_html)   
      return html + header + div + inner_html + end




  def get(self):
      session = get_current_session()
      html = ""
      if 'user' in session:
          user_id = session['user']
          posts = fbmessages.search_contents_for_tagcloud_page(user_id)
          user = fbqueryuser.queryUserFromDataStore(user_id)
          device = self.determine_device()
          audit.add_audit_record(user.facebook_id, user.displayName,'my_tag_cloud_page', self.request.remote_addr, device)
          post_list = []
          logging.info("Count of words before stop words filter" + str(len(posts)))
          for i in range(0,len(posts)-1):
              if (posts[i] not in stopwords.stop_words()):
                  post_list.append(posts[i])

          c = collections.Counter(post_list)
          html = self.generate_html(c)         
      else:
          logging.info("User id not found in session")      
      self.response.out.write(html)

app = webapp2.WSGIApplication([('/tagcloud', TagCloudPosts)],
                              debug=True)

