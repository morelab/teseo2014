# -*- coding: utf-8 -*-
"""
Created on Thu Jun 26 17:03:30 2014

@author: aitor
"""
import gender
import json
import mysql.connector
import time
import gender_detection
import urllib2

import os, sys
lib_path = os.path.abspath('../')
sys.path.append(lib_path)

base_dir = os.path.dirname(os.path.abspath(__file__))

def load_config():
    from model.dbconnection import dbconfig

    return dbconfig
    
def get_names(): 
    config = load_config()
    cnx = mysql.connector.connect(**config)
    cursor = cnx.cursor()
    cursor.execute("SELECT DISTINCT(first_name) FROM person")
    result = set()
    for name in cursor:
        first = name[0].split(' ')[0]
        result.add(first)
    cursor.close()
    cnx.close()

    return list(result)

def update_name_genders():
    name_pool = get_names()
    bad_names = []
    
    config = load_config()
    cnx = mysql.connector.connect(**config)
    cursor = cnx.cursor()

    chunk_size = 50
    total_chunks = len(name_pool)/chunk_size
    rest = len(name_pool)%chunk_size

    for j in range(0, total_chunks):
        print '*******Chunk', j, '/', total_chunks
        names = []
        if j == total_chunks - 1:
            names = name_pool[j * chunk_size:total_chunks*chunk_size+rest]
        else:
            names = name_pool[j * chunk_size:(j+1)*chunk_size]


        gender_list = gender.getGenders(names) #gender, prob, count

        for i, name in enumerate(names):
            infered_gender = gender_list[i][0]
            prob = float(gender_list[i][1])
            #print name, infered_gender, prob
            if infered_gender == 'None' or prob < 0.6:
                bad_names.append(name)
                
            query = "UPDATE person SET gender = '%s' WHERE first_name = '%s'" % (infered_gender, name)
            cursor.execute(query)
            
    
    cursor.close()
    cnx.close()


def get_name_genders_igender():    
    name_pool = get_names()    
    genders = {}
    
    for i, name in enumerate(name_pool):
        if i % 50 == 0:
            print 'Processed', i, 'of', len (name_pool)

        try:
            g, prob = gender_detection.get_gender(name)
            genders[name] = g
            time.sleep(0.1)
        except UnicodeEncodeError:
            genders[name] = 'none'
        except urllib2.HTTPError: 
            print 'Waiting 10 secs'
            time.sleep(10)
            g, prob = gender_detection.get_gender(name)
            genders[name] = g
                

            
            
    json.dump(genders, open('genders_igender.json', 'w'))

                
def update_genders():
    config = load_config()
    cnx = mysql.connector.connect(**config)
    cursor = cnx.cursor()
    
    genders = json.load(open('genders.json', 'r'))
    updated_names = []
    try:
        updated_names = json.load( open('updated_names.json', 'r'))
    except:
        pass
    
    for name in genders:
        if not name in updated_names:            
            query = "UPDATE person SET gender = '%s' WHERE first_name = '%s'" % (genders[name], name)
            cursor.execute(query)
            updated_names.append(name)
      
    try:
        os.remove('updated_names.json')  
    except:
        pass
    json.dump(updated_names, open('updated_names.json', 'w'))
    
    cursor.close()
    cnx.close()
            

    

print 'Updating genders...' 
get_name_genders_igender()        
print 'Done'