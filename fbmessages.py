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
import string
from google.appengine.ext import deferred
from google.appengine.ext import db
from datetime import datetime
from time import strptime
import fbqueryuser



class Posts(db.Model):
    owner = db.StringProperty()
    owner_name = db.StringProperty()
    post_url = db.StringProperty()
    post_datetime = db.DateTimeProperty()
    post_contents = db.StringListProperty()
    post_id = db.StringProperty()
    comment_url = db.StringProperty()
    comment_user_id = db.StringProperty()
    comment_display_name = db.StringProperty()
    comment_id = db.StringProperty()
    post_owner_id = db.StringProperty()
    post_owner_name = db.StringProperty()
    date_time_inserted = db.DateTimeProperty(auto_now=True)
    entry_type = db.StringProperty()


def search_contents_for_tagcloud_page(user_id):
    logging.info("Searching for user id tag cloud entries" + user_id)
    post_list = [] 

    posts = db.GqlQuery("SELECT * FROM Posts " 
             "WHERE owner= :o_id AND post_owner_id = :u_id AND entry_type = :e_type ORDER BY post_datetime DESC LIMIT 1000", o_id=user_id, u_id=user_id, e_type='post')
    
    desc_posts = db.GqlQuery("SELECT * FROM Posts " 
             "WHERE owner= :o_id AND post_owner_id = :u_id AND entry_type = :e_type ORDER BY post_datetime DESC LIMIT 1000", o_id=user_id, u_id=user_id,       e_type='description')
    

    comments = db.GqlQuery("SELECT * FROM Posts " 
        "WHERE owner= :o_id AND comment_user_id = :u_id AND entry_type = :e_type ORDER BY post_datetime DESC LIMIT 1000", o_id=user_id, u_id=user_id, e_type='comment')

    for post in posts:     
        for word in post.post_contents:
            post_list.append(word)

    for d_post in desc_posts:     
        for word_d in d_post.post_contents:
           post_list.append(word_d)

    for comment in comments:  
        for word_c in comment.post_contents:
            post_list.append(word_c)


    return post_list



def search_contents_for_friend_tagcloud_page(user_id ,friend):
    post_list = [] 
    post_id_tracker = {}
    comment_id_tracker = {}

    posts = db.GqlQuery("SELECT * FROM Posts " 
             "WHERE owner= :o_id AND post_owner_id = :u_id AND entry_type = :e_type ORDER BY post_datetime DESC LIMIT 1000", o_id=user_id, u_id=friend, e_type='post')
    
    desc_posts = db.GqlQuery("SELECT * FROM Posts " 
       "WHERE owner= :o_id AND post_owner_id = :u_id AND entry_type = :e_type ORDER BY post_datetime DESC LIMIT 1000", o_id=user_id, u_id=friend, e_type='description')
    

    comments = db.GqlQuery("SELECT * FROM Posts " 
        "WHERE owner= :o_id AND comment_user_id = :u_id AND entry_type = :e_type ORDER BY post_datetime DESC LIMIT 1000", o_id=user_id, u_id=friend, e_type='comment')

    for post in posts: 
        if (post.post_id not in post_id_tracker):  
            post_id_tracker[post.post_id] = post.post_id  
            for word in post.post_contents:
                post_list.append(word)

    for d_post in desc_posts:  
        if (d_post.post_id not in post_id_tracker):  
            post_id_tracker[d_post.post_id] = d_post.post_id  
            for word_d in d_post.post_contents:
               post_list.append(word_d)
   

    for comment in comments:  
        key = comment.comment_id.split('_')[1]
        if (key not in comment_id_tracker):
            logging.info("Comment id not present " + key)
            comment_id_tracker[key] = key
            for word_c in comment.post_contents:
                post_list.append(word_c)
    return post_list



def remove_punctuation(comments):
    return re.sub('[:()*]','',comments)


def trim_url_for_gae(url):
    return url



def find_similar_entry(posts, url):
    for index,post in enumerate(posts):
        if post['post_link'] == url:
            return index,post['from_user']


def to_serializable_list(posts):
    lst = []
    tmp_url_map = {}
    for post in posts:
        postToHashMap ={}
        postToHashMap['post_link'] = post.post_url            
        formatted_date = post.post_datetime.strftime("%d/%m/%Y")
        postToHashMap['created_time'] = formatted_date

        if (post.comment_display_name):
            postToHashMap['from_user'] = post.comment_display_name
        else:
            postToHashMap['from_user'] = post.post_owner_name
        
        if post.post_url not in tmp_url_map:
            lst.append(postToHashMap)
            tmp_url_map[post.post_url] = post.post_url
        else:
            idx, user = find_similar_entry(lst, post.post_url)
            entry = lst[idx]
            if postToHashMap['from_user'] not in entry['from_user'] :
                entry['from_user'] = entry['from_user'] + ',' + postToHashMap['from_user'] 

    return lst
        


def gen_parent_posts_key(posts=None):
    return db.Key.from_path('Posts',posts)


def extract_post_id(post_id):
    if post_id is not None:
        if '_' in post_id:
            lst = post_id.split('_')
            return lst[1]
        else:
            return post_id
    else:
       return post_id


def add_to_datastore_if_new(owner , post_id ,comment_id ,contents ,entry_type): 

    if (post_id is not None and comment_id is None):
        matching_post_ids = db.GqlQuery("SELECT * FROM Posts " 
                                    "WHERE owner= :o_id AND post_id = :p_id AND entry_type = :e_type", o_id=owner, p_id=extract_post_id(post_id), e_type=entry_type)
                            
        if (matching_post_ids.count() > 0):
            return 0 

    if (comment_id is not None):
        matching_comment_ids = db.GqlQuery("SELECT * FROM Posts " 
                                           "WHERE owner= :o_id AND comment_id = :c_id AND post_id = :p_id AND entry_type = :e_type" , 
                                            o_id=owner, c_id=comment_id, p_id=extract_post_id(post_id) , e_type='comment')
        
        if (matching_comment_ids.count() > 0):  
            return 0
    return 1


#
# change this to accept a hashmap of values
def addFacebookEntryToDataStore(feedOwner ,feedOwnerName ,post_id ,url ,contents ,post_owner_id , post_owner_name, created_time=None ,comment_userId=None, commentUserDisplayName=None, comment_url=None , comment_id=None , entry_type=None):

    for c in contents:
        if len(c) > 500:
            logging.info("Single post too long exiting")
            return

    post = Posts(gen_parent_posts_key("Posts"))
    post.post_url=url
    post.post_datetime = created_time
    post.post_contents = contents
    post.owner = feedOwner
    post.owner_name = feedOwnerName
    post.post_id = extract_post_id(post_id)
    post.comment_url = comment_url
    post.comment_user_id = comment_userId
    post.comment_display_name = commentUserDisplayName
    post.comment_id = comment_id
    post.post_owner_id = post_owner_id
    post.post_owner_name = post_owner_name
    post.entry_type = entry_type
    

    # Add logic in here to only put if the date_time for the post owner or comment owner is greater than whats on the database now.
    if add_to_datastore_if_new(feedOwner ,post_id ,comment_id ,contents , entry_type):
        logging.info("Added entry to data store ")
        post.put()

def convertFacebookDate(date):
    stripped_date = date[:19]
    new_date = datetime.strptime(stripped_date, '%Y-%m-%dT%H:%M:%S')
    return new_date

def list_one_is_subset_list_two(search_terms ,post):
    search_terms = filter(lambda x: x.strip() ,search_terms)
    if (set(search_terms).issubset(set(post.post_contents))):
        logging.info("Subset found")   
    return set(search_terms).issubset(set(post.post_contents))

def app_simulate_db_or_statement(search_terms ,posts):
    return filter(lambda x:list_one_is_subset_list_two(search_terms,x),posts)

def find_min_max_post_dates(fbUser):
    user = fbqueryuser.queryUserFromDataStore(fbUser) 
    ''' if user is none its probably because the update hasnt been applied or it hasnt synchronized to all db nodes '''
    if user is None:
        return datetime.now(), datetime.now()

    max_date = Posts.all().filter('owner =',fbUser).order('-post_datetime').fetch(1)
    if len(max_date) > 0:
        latest_post = max_date[0]
        return user.date_account_created,latest_post.post_datetime
    else:
        return datetime.now(), datetime.now()

def detect_post_owner(url):
    logging.info("Url debug" + url)
    regex =re.compile('com/(.*?)/posts')
    m=regex.search(url)
    if (m is None):
        return url
    else:
        post_owner = m.group(1)
        return post_owner


def change_url(logged_in_user, post_url):
    return "https://m.facebook.com/story.php?story_fbid=" + post_url[string.rfind(post_url,'/')+1:]+ "&id=" + detect_post_owner(post_url) + "&__user=" + logged_in_user


def rewrite_url_based_on_agent(posts , isMobileRequest):
    if (isMobileRequest):
        logging.info("Mobile browser request detected ")
        for post in posts:
            post.post_url = change_url(post.owner, post.post_url)
        return posts
            
    else:
        logging.info("Desktop browser request detected ")
        return posts

def find_search_term(search_term , fbUser, isMobileRequest):
    search_term = remove_punctuation(search_term).lower()
    search_terms = filter(lambda x: x.strip() ,search_term.split())
    logging.info("--- In find_search_term ---" + str(len(search_term.split())))
    logging.info(str(search_terms))

    if (len(search_terms) == 0):
        return []
    
    if (len(search_terms) == 1):
        logging.info("Only 1 search term : " + str(search_terms))
        results = Posts.all().filter('post_contents =', search_term.strip()).filter('owner =',fbUser).order('-post_datetime').fetch(100)
        results = rewrite_url_based_on_agent(results, isMobileRequest)
        return results
    else:
        logging.info("Multiple search term : " + str(search_terms))
        posts = Posts.all().filter('post_contents =', search_terms[0]).filter('owner =',fbUser).order('-post_datetime').fetch(100)
        results = app_simulate_db_or_statement(search_terms ,posts )
        results = rewrite_url_based_on_agent(results, isMobileRequest)
        return results



        

def addComments(comments ,wall_owner , ownerName ,this_post_url, post_owner_id_c):
    commentData = comments['data']
    for comment in commentData:
        comment_messageid = comment['id']
        comment_from_user = comment['from']
        comment_display_name = comment_from_user['name']
        comment_from_id = comment_from_user['id']
        comment_message = comment['message']
        comment_message_to_list = remove_punctuation(comment_message).lower().split(" ")
        comment_message_to_list = filter(lambda x: x.strip() ,comment_message_to_list)
        comment_created_time = comment['created_time']
        if (comment_message is not None):
            addFacebookEntryToDataStore(wall_owner ,
                                        ownerName ,
                                        None ,
                                        this_post_url ,
                                        comment_message_to_list ,
                                        post_owner_id_c ,None,
                                        convertFacebookDate(comment_created_time) ,
                                        comment_from_id , 
                                        comment_display_name, 
                                        "http://www.facebook.com",
                                        comment_messageid,'comment')


def processGraphApiJsonMessage(wall_owner ,ownerName ,data , access_token):
    if (len(data) < 1):
        return
    for i in data:       
        this_post_url = ""
        main_message = ""
        main_created_time = ""
        post_owner_id = ""
        post_owner_name = ""
        post_id = ""
        if 'actions' in i:
            action = i['actions']
            for j in action:
		this_post_url = j['link']

        if 'comments' in i:
            comments=i['comments']
            if 'data' in comments:
                post_from = i['from']
                post_owner_id_c = post_from['id']

                if (fbqueryuser.is_a_real_person(post_from)):
                    addComments(comments ,wall_owner , ownerName , trim_url_for_gae(this_post_url), post_owner_id_c)     

        if 'description' in i:            
            description = i['description']
            if 'message' in i:
                description = description + " " + i['message']

            main_created_time= i['created_time']
            message_content_to_list = remove_punctuation(description).lower().split(" ") 
            message_content_to_list = filter(lambda x: x.strip() ,message_content_to_list)
            post_id = i['id']
            post_by_user = i['from']
            post_owner_id = post_by_user['id']
            
            post_owner_name = post_by_user['name']  
            if (fbqueryuser.is_a_real_person(post_by_user)):
                addFacebookEntryToDataStore(wall_owner ,
                                            ownerName ,
                                            post_id ,
                                            trim_url_for_gae(this_post_url) ,
                                            message_content_to_list ,
                                            post_owner_id,
                                            post_owner_name,
                                            convertFacebookDate(main_created_time),entry_type='description'
                                           )                  

        if 'message' in i:
            main_message = i['message']
            main_created_time= i['created_time']
            message_content_to_list = remove_punctuation(main_message).lower().split(" ") 
            message_content_to_list = filter(lambda x: x.strip() ,message_content_to_list)
            post_id = i['id']
            post_by_user = i['from']
            post_owner_id = post_by_user['id']
            post_owner_name = post_by_user['name']
            
            if (fbqueryuser.is_a_real_person(post_by_user)):
                addFacebookEntryToDataStore(wall_owner ,
                                            ownerName ,
                                            post_id ,
                                            trim_url_for_gae(this_post_url) ,
                                            message_content_to_list ,
                                            post_owner_id,
                                            post_owner_name,
                                            convertFacebookDate(main_created_time),entry_type='post'
                                           )





