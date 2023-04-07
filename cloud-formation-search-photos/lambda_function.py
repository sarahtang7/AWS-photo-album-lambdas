import base64
import json
import time
from datetime import *
import boto3
import re
import inflection
import requests
from requests_aws4auth import AWS4Auth
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth

region = 'us-east-1'
service = 'es'
credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, service, session_token=credentials.token)

bucket_url = 'https://s3.amazonaws.com/cf-photos-bucket-2/'

def get_imgs(label):
    search_url = 'https://search-cf-photos-hnsoyvkb5haubxfwsuex2pkgui.us-east-1.es.amazonaws.com/photos/_search'
    print('label:', label)
    url = search_url
    if(label != 'all'):
        url = search_url + '?q=' + label
    resp = requests.get(url, auth=awsauth)
    return resp.text
        
def lambda_handler(event, context):
    print("testing pipeline to redeployed CF lambda functions! (search photos)")
    img_urls = []
    
    # testing display on front-end
    print('event: ', json.dumps(event))
    
    ##IMPLEMENT ERROR HANDLING IF LEX INTENT NOT FULFILLED##
    
    if(event == [] or event =='' or event =={}):
        return {
            'statusCode': 200,
            'headers': {
                "Access-Control-Allow-Origin": "*",
                'Content-Type': 'application/json'
            },
            'body': json.dumps({"images": []})
        }
    
    # Get input query
    query = event["queryStringParameters"]["q"]
    print("query:",query)
    
    #TESTING
    queries = ['cats and dogs', 'photos with cats and dogs', 'show me photos with bunnies', 'show me photos with carrots']
    ######
    
    # Initialize Lexbot and get output message
    client = boto3.client('lexv2-runtime')
    response = client.recognize_text(
        botId='UGOVFNGXZV', # MODIFY HERE
        botAliasId='VJGQILWXLN', # MODIFY HERE
        localeId='en_US',
        sessionId='testuser',
        text=query)
    print('Response:', response)
    
    lex_resp = response['sessionState']['intent']['slots']
    print(lex_resp)
    
    slots = []
    if(lex_resp != None and lex_resp != ' '):
        for q in lex_resp:
            if(lex_resp[q] != None):
                #print(lex_resp[q])
                val = lex_resp[q]['value']['interpretedValue']
                # TRANSFORM VAL TO SINGULAR HERE
                val = inflection.singularize(val).lower()
                slots.append(val)
        
    print('Slots:',slots)
    
    for slot in slots:
        os_data = json.loads(get_imgs(slot))
        print('Data:', os_data)
        hits = os_data['hits']['hits']
        print('Hits:',hits)
        
        if(hits != None and hits != []):
            for hit in hits:
                obj_label = hit['_source']['objectKey']
                #print(obj_label)
                url = bucket_url + str(obj_label)
                #print(url)
                if url not in img_urls:
                    img_urls.append(url)
            

    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Headers': '*',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': '*',
            'Content-Type': 'application/json'
        },
        'body': json.dumps({"images": img_urls})
    }