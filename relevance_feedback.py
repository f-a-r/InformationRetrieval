#!/usr/bin/env python
# -*- coding: utf-8 -*-
import nltk
import urllib2
import base64
import json
import sys
import string
import re
import math
from numpy  import *

def create_dictionary(queries, results, feedbacks, stopwords, iteration, rel, nonRel, docs, dfi):
    
    for i in range(10):
        
        if feedbacks[i] > 0: # decide which doc is rel
            rel.append(i + iteration*10)
        else:
            nonRel.append(i + iteration*10)

        doc = {} # create a dict for each doc

        # add words from titles
        words = nltk.tokenize.wordpunct_tokenize(  re.sub(r'[^\w]', ' ', results[i]['Title'].lower()) )
        words = [str(w) for w in words]
        for w in words:
            if w not in stopwords:
                if w not in queries:
                    queries[w] = 0
                if w not in doc:
                    doc[w] = 1
                else:
                    doc[w] += 1

        # add words from description
        words = nltk.tokenize.wordpunct_tokenize(  re.sub(r'[^\w]', ' ', results[i]['Description'].lower()) )
        words = [str(w) for w in words]
        for w in words:
            if w not in stopwords:
                if w not in queries:
                    queries[w] = 0
                if w not in doc:
                    doc[w] = 1
                else:
                    doc[w] += 1

        # append this doc to our doc list
        docs.append(doc)

    for d in range(len(docs)): # to unify the vector words of both rel/nonrel (i.e., both have the same set of words)
        for q in queries:
            if q not in docs[d]:
                docs[d][q] = 0

    # idf
    word_list = queries.keys()
    for w in word_list: # for words haven't be in dfi, give them init values 0.0
        if w not in dfi:
            dfi[w] = 0.000001

    for i in range(10):
        content = []
        title = nltk.tokenize.wordpunct_tokenize(  re.sub(r'[^\w]', ' ', results[i]['Title'].lower()) )
        description = nltk.tokenize.wordpunct_tokenize(  re.sub(r'[^\w]', ' ', results[i]['Description'].lower()) )
        content.extend(title)
        content.extend(description)
        content = [str(w) for w in content]
        for w in word_list:
            if w in content:
                dfi[w] += 1

    
    #dfi_s = [(w, dfi[w]) for w in dfi]
    #dfi_s = sorted(dfi_s, key=lambda tup: tup[1], reverse=True) 
    #print dfi_s

    #for w in dfi:
    #    if dfi[w] == 0:
    #        print 'word with 0 dfi: ' + w

    idf = {}
    for w in word_list:
        idf[w] = math.log(len(docs)/dfi[w])

    return rel, nonRel, queries, docs, idf, dfi

def update_queries(queries, queries_bing, rel, nonRel, docs, idf):
    #Giving default values to a, b and c
    a = 1
    b = 0.8
    c = 0.1
    rel_size = len(rel)
    nonRel_size = len(nonRel)
    word_list = sorted(queries.keys()) # sorted current word list
    word_count = len(word_list) # num of current words
    query_vec = array([queries[x] for x in word_list]) # the query vector
    query_vec = query_vec/linalg.norm(query_vec,2) # normalizing the query vector
    
    sum_rel_vec = array([0.0]*word_count) # creating an array for sum of relevant words vector result
    for i in rel:
        doc_vec = array([docs[i][x] for x in word_list]) # the doc vector
        doc_vec = doc_vec/linalg.norm(doc_vec,2) #normalizing words in each document (l2-norm)
        sum_rel_vec += doc_vec #adding them to the sum of vectors
    sum_rel_vec /= rel_size # divided by num of rel docs

    sum_nonrel_vec = array([0.0]*word_count)   #creating an array for sum of non relevant words vector result
    for i in nonRel:
        doc_vec = array([docs[i][x] for x in word_list])
        doc_vec = doc_vec/linalg.norm(doc_vec,2)
        sum_nonrel_vec += doc_vec
    sum_nonrel_vec /= nonRel_size

    query_vec = a*query_vec + b*sum_rel_vec - c*sum_nonrel_vec # Rocchio Formula

    for i in range(word_count): # update the new query scores for next iteration
        queries[word_list[i]] = query_vec[i]
    
    idf_vec = array([idf[x] for x in word_list]) # create an array for idf weights
    query_vec_weigh = query_vec*idf_vec # weight the query vector by idf (tfidf)

    word_list_weight = [(word_list[i], query_vec_weigh[i]) for i in range(word_count)]
    word_list_weight = sorted(word_list_weight, key=lambda tup: tup[1], reverse=True) # sort the potiential query words based on their scores
    
    counter = 0 # adding the two potiential query words with highest scores but are not already in our query list
    for w in word_list_weight:
        if w[0] not in queries_bing:
            queries_bing.append(w[0])
            counter += 1
            if (counter >= 2): break
            
    #print 'queries_bing'
    #print queries_bing
    
    #for i in range(word_count):
    #    print '%s = %f'%(word_list_weight[i][0], word_list_weight[i][1])

    return queries, queries_bing

def main():

    accKey = sys.argv[1]
    prec_target = float(sys.argv[2])
    queries_input = sys.argv[3:]

    queries_bing = queries_input

    queries = {}
    for q in queries_input:
        queries[q] = 1
    
    for line in open('stopwords.txt'):
        stopwords = string.split(string.strip(line), ',')

    print 'Parameters:'
    print 'Query: ',
    print queries_input
    print 'Precision required: ' + str(prec_target)
    print 'Total number of results: 10'
    print '========================================'

    prec = 0
    iteration = 0
    rel = []
    nonRel = []
    dfi = {}
    docs = []
    while(True):
        
        #bingUrl = 'https://api.datamarket.azure.com/Bing/Search/Web?Query=%27gates%27&$top=10&$format=JSON'
        bingUrl = 'https://api.datamarket.azure.com/Bing/Search/Web?Query=%27'+'+'.join(queries_bing)+'%27&$top=10&$format=JSON'  
        print 'URL: ' + bingUrl
        print 'Queries: ',
        print queries_bing
        print '========================================'
        #Provide your account key here
        accountKey = accountKey

        accountKeyEnc = base64.b64encode(accountKey + ':' + accountKey)
        headers = {'Authorization': 'Basic ' + accountKeyEnc}
        req = urllib2.Request(bingUrl, headers = headers)
        response = urllib2.urlopen(req)
        #content = response.read()
        content = unicode(response.read(),"utf-8",errors="ignore")
        #content contains the xml/json response from Bing. 
        content = json.loads(content) #keys: [u'd']
        content = content[u'd'] #keys: [u'results', u'__next']
        #print content[u'results']
        #[u'Description', u'Title', u'Url', u'__metadata', u'DisplayUrl', u'ID']
        
        #If in the first iteration there are fewer than 10 results overall, then your program should simply terminate
        results_count = len(content[u'results'])
        if (results_count < 10):
            if (iteration == 0):
                print 'In the first iteration there are fewer than 10 results, exit'
                exit()
            else:
                if results_count < 1:
                    print 'No result returned, exit'
                    exit()
                else:
                    for r in range(results_count, 10):
                        content[u'results'].append(content[u'results'][0])

        feedbacks = []
        print 'Bing Search Results (iteration %d):'%iteration
        for i in range(results_count):
            print'['
            print 'Result ' + str(i+1) + ':'
            print content[u'results'][i]['Title']
            print content[u'results'][i]['Url']
            print content[u'results'][i]['Description']
            print ']'
            print '\n'
            feedbacks.append(int(raw_input('Relevant? (1:yes, 0:no)')))
        #feedbacks = [0,0,1,1,1,0,1,0,0,1]

        # deal with the case of results returned least than 10
        if (results_count < 10):
            for r in range(results_count, 10):
                    feedbacks.append(feedbacks[0])

        #print feedbacks[:results_count]
        prec = sum(feedbacks[:results_count])/float(results_count)
        
        if prec == 0.0:
            print '\n'
            print '========================================'
            print 'FEEDBACK SUMMARY'
            print 'Queries: ',
            print queries_bing
            print 'Precision: ' + str(prec)
            print 'Precision is 0.0, exit'
            print '========================================'
            break

        if (prec >= prec_target):
            print '\n'
            print '========================================'
            print 'FEEDBACK SUMMARY'
            print 'Queries: ',
            print queries_bing
            print 'Precision: ' + str(prec)
            print 'Desired precision reached, done'
            print '========================================'
            break
        else:
            print '\n'
            print '========================================'
            print 'FEEDBACK SUMMARY'
            print 'Queries:',
            print queries_bing
            print 'Precision: ' + str(prec)
            print 'Still below the desired precision of ' + str(prec_target)
            print '========================================' 
            rel, nonRel, queries, docs, idf, dfi = create_dictionary(queries, content[u'results'], feedbacks, stopwords, iteration, rel, nonRel, docs, dfi)
            queries, queries_bing = update_queries(queries, queries_bing, rel, nonRel, docs, idf)
            iteration += 1


main()