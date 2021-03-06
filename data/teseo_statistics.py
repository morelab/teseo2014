# -*- coding: utf-8 -*-
"""
Created on Tue Feb 18 11:20:55 2014

@author: aitor
"""

import mysql.connector
from cache import university_locations, university_ids, thesis_ids, name_genders, codes_descriptor, descriptor_codes
import networkx as nx
import sys
import pprint
import json

import os
lib_path = os.path.abspath('../')
sys.path.append(lib_path)
from model.dbconnection import dbconfig

config = dbconfig

#*******************
#  SNA
#*******************

def build_panel_relations():
    cnx = mysql.connector.connect(**config)
    cursor = cnx.cursor()
    G = nx.Graph()
    for cont, thesis in enumerate(thesis_ids):
        if cont%500 == 0:
            print 'Creating panel relations network: ' + str(float(cont)/len(thesis_ids) * 100)
        query = 'SELECT person.name FROM panel_member, person WHERE panel_member.person_id = person.id AND panel_member.thesis_id =' + str(thesis)
        cursor.execute(query)
        panel = []
        for person in cursor:
            panel.append(person[0])
        for i, person in enumerate(panel):
            source = person
            for j in range(i+1, len(panel)):
                target = panel[j]
                if G.has_edge(source, target):
                    G.edge[source][target]['weight'] += 1
                else:
                    G.add_edge(source, target, weight = 1)
    cursor.close()
    print 'Graph created'
    print '-Nodes:',len(G.nodes())
    print '-Edges:',len(G.edges())

    return G

def build_area_relations():
    cnx = mysql.connector.connect(**config)
    cursor = cnx.cursor()
    g_3 = nx.Graph()
    g_2 = nx.Graph()
    g_1 = nx.Graph()
    for cont, thesis in enumerate(thesis_ids):
        if cont%500 == 0:
            print 'Creating area relations network: ' + str(float(cont)/len(thesis_ids) * 100)

        query = 'SELECT descriptor.code FROM descriptor, association_thesis_description WHERE association_thesis_description.descriptor_id = descriptor.id AND association_thesis_description.thesis_id =' + str(thesis)
        cursor.execute(query)
        descriptors = []
        for descriptor in cursor:
            descriptors.append(str(descriptor[0]))

        for i, descriptor in enumerate(descriptors):
            source_3 = codes_descriptor[descriptor]
            source_2 = codes_descriptor[descriptor[:4] +'00']
            source_1 = codes_descriptor[descriptor[:2] + '0000']
            for j in range(i+1, len(descriptors)):
                target_3 = codes_descriptor[descriptors[j]]
                target_2 = codes_descriptor[descriptors[j][:4] + '00']
                target_1 = codes_descriptor[descriptors[j][:2] + '0000']
                
                if g_3.has_edge(source_3, target_3):
                    g_3.edge[source_3][target_3]['weight'] += 1
                else:
                    g_3.add_edge(source_3, target_3, weight = 1)
                
                if g_2.has_edge(source_2, target_2):
                    g_2.edge[source_2][target_2]['weight'] += 1
                else:
                    g_2.add_edge(source_2, target_2, weight = 1)

                if g_1.has_edge(source_1, target_1):
                    g_1.edge[source_1][target_1]['weight'] += 1
                else:
                    g_1.add_edge(source_1, target_1, weight = 1)                    

    cursor.close()
    print 'Third level'
    print '-Nodes:',len(g_3.nodes())
    print '-Edges:',len(g_3.edges())
    
    print 'Second level'
    print '-Nodes:',len(g_2.nodes())
    print '-Edges:',len(g_2.edges())

    print 'First level'
    print '-Nodes:',len(g_1.nodes())
    print '-Edges:',len(g_1.edges())


    return g_3, g_2, g_1



#the graph is too big. Nodes with not enough degree are deleted
#If a node has a degree of 4 or less it only has been in the panel of 1 viva
def filter_panel_relations(G, MIN_DEGREE = 5):
    print 'Starting graph'
    print '-Nodes:',len(G.nodes())
    print '-Edges:',len(G.edges())
    continue_cleaning = True
    while(continue_cleaning):
        degrees = G.degree()
        total_removed = 0
        for d in degrees:
            if degrees[d] < MIN_DEGREE:
                G.remove_node(d)
                total_removed += 1
        if total_removed == 0:
            continue_cleaning = False
        else:
            print 'Deleted:', total_removed
    print 'Filtered graph'
    print '-Nodes:',len(G.nodes())
    print '-Edges:',len(G.edges())


#***********************
#  Simple statistics
#***********************


def get_university_ids():
    cnx = mysql.connector.connect(**config)
    cursor_unis = cnx.cursor()
    cursor_unis.execute("SELECT id, name FROM university")
    result = {}
    for university in cursor_unis:
        result[university[0]] = university[1]
    cursor_unis.close()
    return result

def get_number_phd_by_universities():
    cnx = mysql.connector.connect(**config)
    cursor = cnx.cursor()
    result = {}
    for key in university_ids.keys():
        uni_name = university_ids[key]
        query = 'SELECT COUNT(*) FROM thesis WHERE university_id=' + str(key)
        cursor.execute(query)
        for count in cursor:
            result[uni_name] = count[0]
    cursor.close()

    return result



def create_university_temporal_evolution_by_year():
    cnx = mysql.connector.connect(**config)
    cursor = cnx.cursor()
    query = 'SELECT university_id, defense_date from thesis'
    cursor.execute(query)
    results = {2000:{u'DEUSTO':0}}
    for i, thesis in enumerate(cursor):
        if i%500 == 0:
            print 'Universities temporal evolution', i

        try:
            university = university_ids[thesis[0]]
            year = thesis[1].year
            if year in results.keys():
                unis = results[year]
                if university in unis.keys():
                    unis[university] += 1
                else:
                    unis[university] = 1
            else:
                results[year] = {university:1}
        except AttributeError:
            print 'The thesis has no year in the database'
        except KeyError:
            print 'Unkown university:', thesis[0]
        except TypeError:
            print 'The thesis has no related university'
            
    cursor.close()
    return results

def create_region_temporal_evolution_by_year():
    by_university = create_university_temporal_evolution_by_year()
    by_region = {}
    for year in by_university:
        universities = by_university[year]
        for uni in universities:
            region = university_locations[uni]
            total_uni = universities[uni]
            if year in by_region.keys():
                regions = by_region[year]
                if region in regions.keys():
                    regions[region] += total_uni
                else:
                    regions[region] = total_uni
            else:
                by_region[year] = {region:total_uni}

    return by_region

def create_area_temporal_evolution_by_year():
    cnx = mysql.connector.connect(**config)
    cnx2 = mysql.connector.connect(**config)
    cursor = cnx.cursor()
    query = 'SELECT id, defense_date from thesis'
    cursor.execute(query)
    results = {}
    for i, thesis in enumerate(cursor):
        try:
            thesis_id = thesis[0]
            year = thesis[1].year
            if i%500 == 0:
                print 'Unesco code temporal evolution, processing', thesis_id, ', year', year

            #get descriptors
            cursor_desc = cnx2.cursor()
            query_desc = 'SELECT descriptor.code FROM association_thesis_description, descriptor WHERE association_thesis_description.thesis_id=' + str(thesis_id) + ' AND association_thesis_description.descriptor_id=descriptor.id'
            cursor_desc.execute(query_desc)

            used_descriptors = []
            for desc in cursor_desc:
                used_descriptors.append(desc[0])
            cursor_desc.close()


            if year in results.keys():
                descs = results[year]
                for descriptor_id in used_descriptors:
                    decriptor_text = codes_descriptor[str(descriptor_id)]
                    if decriptor_text in descs.keys():
                        descs[decriptor_text] += 1
                    else:
                        descs[decriptor_text] = 1
            else:
                descs = {}
                for descriptor_id in used_descriptors:
                    decriptor_text = codes_descriptor[str(descriptor_id)]
                    descs[decriptor_text] = 1
                results[year] = descs
        except AttributeError:
            print 'The thesis has no year in the database'
        except mysql.connector.errors.InternalError as ie:
            print 'Mysql error', ie.msg
    cursor.close()
    return results

#only uses first level area codes ##0000
def create_meta_area_temporal_evolution_by_year():
    cnx = mysql.connector.connect(**config)
    cnx2 = mysql.connector.connect(**config)
    cursor = cnx.cursor()
    query = 'SELECT id, defense_date from thesis'
    cursor.execute(query)
    results = {}
    for i, thesis in enumerate(cursor):
        try:
            thesis_id = thesis[0]
            year = thesis[1].year
            if i%500 == 0:
                print 'First level Unesco code temporal evolution, processing', thesis_id, ', year', year

            cursor_desc = cnx2.cursor()
            query_desc = 'SELECT descriptor.code FROM association_thesis_description, descriptor WHERE association_thesis_description.thesis_id=' + str(thesis_id) + ' AND association_thesis_description.descriptor_id=descriptor.id'
            cursor_desc.execute(query_desc)

            used_descriptors = set()
            for desc in cursor_desc:
                try:
                    descriptor_text = codes_descriptor[str(desc[0])]
                    descriptor_code = descriptor_codes[descriptor_text]
                    first_level_code = descriptor_code[0:2] + '0000'
                    first_level_descriptor = codes_descriptor[first_level_code]
                    used_descriptors.add(first_level_descriptor)
                except:
                    print 'No data', descriptor_text
            cursor_desc.close()


            if year in results.keys():
                descs = results[year]
                for d in used_descriptors:
                    if d in descs.keys():
                        descs[d] += 1
                    else:
                        descs[d] = 1
            else:
                descs = {}
                for d in used_descriptors:
                    descs[d] = 1
                results[year] = descs
        except AttributeError:
            print 'The thesis has no year in the database'
        except mysql.connector.errors.InternalError as ie:
            print 'Mysql error', ie.msg
    cursor.close()
    return results

def create_gender_temporal_evolution_by_year():
    cnx = mysql.connector.connect(**config)
    cursor = cnx.cursor()
    query = 'SELECT person.first_name, thesis.author_id, thesis.defense_date FROM thesis, person WHERE thesis.author_id = person.id'
    cursor.execute(query)
    results = {}
    for i, thesis in enumerate(cursor):
        if i%500 == 0:
            print 'Genders temporal evolution', i

        try:
            name = thesis[0].split(' ')[0] #if it is a composed name we use only the first part to identify the gender

            try:
                gender = name_genders[name]
            except KeyError:
                gender = 'None'
            year = thesis[2].year
            if year in results.keys():
                genders = results[year]
                if gender in genders.keys():
                    genders[gender] += 1
                else:
                    genders[gender] = 1
            else:
                results[year] = {gender:1}
        except AttributeError:
            print 'The thesis has no year in the database'
    cursor.close()
    return results

def create_gender_percentaje_evolution(gender_temp):
    result= {}
    for year in gender_temp:
        try:
            total_year = float(gender_temp[year]['female'] + gender_temp[year]['male'])
            female_perc = gender_temp[year]['female']/total_year
            male_perc = gender_temp[year]['male']/total_year
            result[year] = {'female':female_perc, 'male':male_perc}
        except:
            pass
    return result

def create_gender_per_area_evolution():
    cnx = mysql.connector.connect(**config)
    cnx2 = mysql.connector.connect(**config)
    cursor = cnx.cursor()
    query = 'SELECT person.first_name, thesis.id, thesis.defense_date FROM thesis, person WHERE thesis.author_id = person.id'
    cursor.execute(query)
    results = {}
    for i, thesis in enumerate(cursor):
        if i%500 == 0:
            print 'Genders per Unesco code temporal evolution', i
        try:

            #get gender
            name = thesis[0].split(' ')[0] #if it is a composed name we use only the first part to identify the gender
            try:
                gender = name_genders[name]
            except KeyError:
                gender = 'None'

            #get descriptors
            thesis_id = thesis[1]
            cursor_desc = cnx2.cursor()
            query_desc = 'SELECT descriptor.code FROM association_thesis_description, descriptor WHERE association_thesis_description.thesis_id=' + str(thesis_id) + ' AND association_thesis_description.descriptor_id=descriptor.id'
            cursor_desc.execute(query_desc)

            used_descriptors = []
            for desc in cursor_desc:
                used_descriptors.append(desc[0])
            cursor_desc.close()

            year = thesis[2].year

            if year in results.keys():
                descs = results[year]
                for descriptor_id in used_descriptors:
                    decriptor_text = codes_descriptor[str(descriptor_id)]
                    if decriptor_text in descs.keys():
                        gender_area = descs[decriptor_text]
                        if gender in gender_area.keys():
                            gender_area[gender] += 1
                        else:
                            gender_area[gender] = 1
                    else:
                        descs[decriptor_text] = {gender:1}
            else:
                descs = {}
                for descriptor_id in used_descriptors:
                    decriptor_text = codes_descriptor[str(descriptor_id)]
                    descs[decriptor_text] = {gender:1}
                results[year] = descs


        except AttributeError:
            print 'The thesis has no year in the database'
        except mysql.connector.errors.InternalError as ie:
            print 'Mysql error', ie.msg
    cursor.close()
    return results

def create_gender_panel_evolution_by_year():
    cnx = mysql.connector.connect(**config)
    cnx2 = mysql.connector.connect(**config)
    cursor = cnx.cursor()
    query = 'SELECT thesis.id, thesis.defense_date from thesis'
    cursor.execute(query)
    results = {}
    for i, thesis in enumerate(cursor):
        if i%500 == 0:
            print 'Thesis panel gender distribution temporal evolution', i
        cursor_names = cnx2.cursor()
        query_names = 'SELECT person.first_name FROM panel_member, person WHERE person.id = panel_member.person_id AND panel_member.thesis_id=' + str(thesis[0])
        cursor_names.execute(query_names)
        genders = {'male':0, 'female':0, 'None':0}
        for name in cursor_names:
            try:
                gender = name_genders[name[0]]
            except:
                gender = 'None'
            genders[gender] += 1
        cursor_names.close()



        try:
            year = thesis[1].year
            if year in results.keys():
                gender_cont = results[year]
                for g in genders:
                    if g in gender_cont.keys():
                        gender_cont[g] += genders[g]
                    else:
                        gender_cont[g] = genders[g]
            else:
                results[year] = genders
        except AttributeError:
            print 'The thesis has no year in the database'

    cursor.close()

    return results
    
    
def create_gender_advisor_evolution_by_year():
    cnx = mysql.connector.connect(**config)
    cnx2 = mysql.connector.connect(**config)
    cursor = cnx.cursor()
    query = 'SELECT thesis.id, thesis.defense_date from thesis'
    cursor.execute(query)
    results = {}
    for i, thesis in enumerate(cursor):
        if i%500 == 0:
            print 'Thesis advisor gender distribution temporal evolution', i
        cursor_names = cnx2.cursor()
        query_names = 'SELECT person.first_name FROM advisor, person WHERE person.id = advisor.person_id AND advisor.thesis_id=' + str(thesis[0])
        cursor_names.execute(query_names)
        genders = {'male':0, 'female':0, 'None':0}
        for name in cursor_names:
            try:
                gender = name_genders[name[0]]
            except:
                gender = 'None'
            genders[gender] += 1
        cursor_names.close()



        try:
            year = thesis[1].year
            if year in results.keys():
                gender_cont = results[year]
                for g in genders:
                    if g in gender_cont.keys():
                        gender_cont[g] += genders[g]
                    else:
                        gender_cont[g] = genders[g]
            else:
                results[year] = genders
        except AttributeError:
            print 'The thesis has no year in the database'

    cursor.close()

    return results


def create_gender_meta_area_evolution():
    cnx = mysql.connector.connect(**config)
    cnx2 = mysql.connector.connect(**config)
    cursor = cnx.cursor()
    query = 'SELECT person.first_name, thesis.id, thesis.defense_date FROM thesis, person WHERE thesis.author_id = person.id'
    cursor.execute(query)
    results = {}
    for i, thesis in enumerate(cursor):
        if i%500 == 0:
            print 'Genders per first level Unesco code temporal evolution', i
        try:

            #get gender
            name = thesis[0].split(' ')[0] #if it is a composed name we use only the first part to identify the gender
            try:
                gender = name_genders[name]
            except KeyError:
                gender = 'None'

            #get descriptors
            thesis_id = thesis[1]
            cursor_desc = cnx2.cursor()
            query_desc = 'SELECT descriptor.code FROM association_thesis_description, descriptor WHERE association_thesis_description.thesis_id=' + str(thesis_id) + ' AND association_thesis_description.descriptor_id=descriptor.id'
            cursor_desc.execute(query_desc)

            used_descriptors = set()
            for desc in cursor_desc:
                try:
                    descriptor_text = codes_descriptor[str(desc[0])]
                    descriptor_code = descriptor_codes[descriptor_text]
                    first_level_code = descriptor_code[0:2] + '0000'
                    first_level_descriptor = codes_descriptor[first_level_code]
                    used_descriptors.add(first_level_descriptor)
                except TypeError:
                    print 'Thesis has no unesco codes'
            cursor_desc.close()

            year = thesis[2].year

            if year in results.keys():
                descs = results[year]
                for decriptor_text in used_descriptors:
                    if decriptor_text in descs.keys():
                        gender_area = descs[decriptor_text]
                        if gender in gender_area.keys():
                            gender_area[gender] += 1
                        else:
                            gender_area[gender] = 1
                    else:
                        descs[decriptor_text] = {gender:1}
            else:
                descs = {}
                for decriptor_text in used_descriptors:
                    descs[decriptor_text] = {gender:1}
                results[year] = descs


        except AttributeError:
            print 'The thesis has no year in the database'
        except mysql.connector.errors.InternalError as ie:
            print 'Mysql error', ie.msg
    cursor.close()
    return results

def create_month_distribution():
    cnx = mysql.connector.connect(**config)
    cursor = cnx.cursor()
    query = 'SELECT thesis.defense_date FROM thesis'
    cursor.execute(query)
    results = {}

    for i, date in enumerate(cursor):
         if i%500 == 0:
             print 'Month distribution', i
         try:
             month = date[0].month
         except AttributeError:
             print 'Thesis has no date'
         if month in results.keys():
             results[month] += 1
         else:
             results[month] = 1

    cursor.close()
    return results
    
def create_university_areas():
    cnx = mysql.connector.connect(**config)
    cursor = cnx.cursor()
    query = '''SELECT thesis.defense_date, university.name, descriptor.code  
               FROM thesis, university, descriptor, association_thesis_description 
               WHERE thesis.id = association_thesis_description.thesis_id 
               AND association_thesis_description.descriptor_id = descriptor.id
               AND thesis.university_id = university.id'''
    cursor.execute(query)
    results_by_uni = {}   #{DEUSTO:{'2000':{'INFORMATICA':1}}}
    results_by_code = {}   #{INFORMATICA:{'2000':{'DEUSTO':1}}}

    for i, info in enumerate(cursor):
         if i%500 == 0:
             print 'University areas', i
         try:
             year = info[0].year
             university = info[1]
             code = str(info[2])[:4] + '00'
             code = codes_descriptor[code]
         except AttributeError:
             print 'Thesis has no date'
             
         if university in results_by_uni.keys():
             years = results_by_uni[university]
             if year in years.keys():
                 codes = years[year]
                 if code in codes.keys():
                     codes[code] += 1
                 else:
                     codes[code] = 1  
             else:
                 years[year] = {code:1}          
         else:
             results_by_uni[university] = {year:{code:1}}
        
         if code in results_by_code.keys():
             years = results_by_code[code]
             if year in years.keys():
                 universities = years[year]
                 if university in universities.keys():
                     universities[university] += 1
                 else:
                     universities[university] = 1  
             else:
                 years[year] = {university:1}          
         else:
             results_by_code[code] = {year:{university:1}}
        
        
         

    cursor.close()
    return results_by_uni, results_by_code
    


if __name__=='__main__':

    print 'Calculating statistics and graphs'
    pp = pprint.PrettyPrinter(indent=4)

#    #create the thesis panel social network
#    G = build_panel_relations()
#    filter_panel_relations(G)
#    print 'Writing file'
#    nx.write_gexf(G, '../website/static/data/panel_relations_filtered.gexf')
#
#    #create the social network for the thematic areas
#    g_3, g_2, g_1 = build_area_relations()
#    print 'Writing files'
#    nx.write_gexf(g_3, '../website/static/data/3_level_unesco_relations.gexf')
#    nx.write_gexf(g_2, '../website/static/data/2_level_unesco_relations.gexf')
#    nx.write_gexf(g_1, '../website/static/data/1_level_unesco_relations.gexf')

#    #Create the temporal evolution of the universities
#    print 'Temporal evolution of the universities'
#    unis = create_university_temporal_evolution_by_year()
#    pp.pprint(unis)
#    json.dump(unis, open('../website/static/data/universities_temporal.json', 'w'), indent = 4)
#
#    #Create the temporal evolution of the geoprahpical regions
#    print 'Temporal evolution of the geoprahpical regions'
#    regions = create_region_temporal_evolution_by_year()
#    pp.pprint(regions)
#    json.dump(regions, open('../website/static/data/regions_temporal.json', 'w'), indent = 4)
#
#    #Create the temporal evolution of the knowledge areas
#    print 'Temporal evolution of the knowledge areas'
#    areas = create_area_temporal_evolution_by_year()
#    pp.pprint(areas)
#    json.dump(areas, open('../website/static/data/areas_temporal.json', 'w'), indent = 4)
#
#    #Create the temporal evolution of the author genders
#    print 'Temporal evolution of the author genders'
#    genders_total = create_gender_temporal_evolution_by_year()
#    pp.pprint(genders_total)
#    json.dump(genders_total, open('../website/static/data/genders_total.json', 'w'), indent = 4)
#
#    #Create the temporal evolution of gender percentage
#    print 'Temporal evolution of gender percentage'
#    genders_percentage = create_gender_percentaje_evolution(genders_total)
#    pp.pprint(genders_percentage)
#    json.dump(genders_percentage, open('../website/static/data/genders_percentage.json', 'w'), indent = 4)
#
#    #create the temporal evolution of gender per area
#    print 'Temporal evolution of gender percentage per area'
#    genders_area_total = create_gender_per_area_evolution()
#    pp.pprint(genders_area_total)
#    json.dump(genders_area_total, open('../website/static/data/genders_area_total.json', 'w'), indent = 4)
#
#    #Create the temporal evolution of the primary knowledge areas
#    print 'Temporal evolution of the knowledge areas'
#    primary_areas = create_meta_area_temporal_evolution_by_year()
#    pp.pprint(primary_areas)
#    json.dump(primary_areas, open('../website/static/data/first_level_areas_temporal.json', 'w'), indent = 4)
#
#     #Create the temporal evolution of panel members' gender
#    print 'Temporal evolution of the panel members\' gender areas'
#    panel_gender = create_gender_panel_evolution_by_year()
#    pp.pprint(panel_gender)
#    json.dump(panel_gender, open('../website/static/data/gender_panel_temporal.json', 'w'), indent = 4)
#
#    #Create the temporal evolution of the genders in first level areas
#    print 'Temporal evolution of the student genders by first level area'
#    meta_area_gender = create_gender_meta_area_evolution()
#    pp.pprint(meta_area_gender)
#    json.dump(meta_area_gender, open('../website/static/data/gender_first_level_areas_temporal.json', 'w'), indent = 4)
#
#     #Create the temporal evolution of the genders of the thesis advisors
#    print 'Temporal evolution of the advisors genders'
#    advisor_gender = create_gender_advisor_evolution_by_year()
#    pp.pprint(advisor_gender)
#    json.dump(advisor_gender, open('../website/static/data/advisor_gender.json', 'w'), indent = 4)
#
#    #create month distribution
#    print 'Month distribution'
#    month_distribution = create_month_distribution()
#    pp.pprint(month_distribution)
#    json.dump(month_distribution, open('../website/static/data/month_distribution.json', 'w'), indent = 4)
#
    #create second level area temporal evolution per university and year
    print 'Area temporal evolution per university and year'
    results_by_uni, results_by_code = create_university_areas()
    pp.pprint(results_by_uni)
    json.dump(results_by_uni, open('../website/static/data/university_area_year_by_uni.json', 'w'), indent = 4)
    
    pp.pprint(results_by_code)
    json.dump(results_by_code, open('../website/static/data/university_area_year_by_code.json', 'w'), indent = 4)
    
    

    print '********** DONE  *************'


