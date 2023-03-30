import base64
import json
import time
import inflection
from datetime import *
import boto3
import re
import requests
from requests_aws4auth import AWS4Auth
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth

host = 'https://search-photos2-iso42y4zytwc3luoezg7cfftpe.us-east-1.es.amazonaws.com'
HOST = 'search-photos2-iso42y4zytwc3luoezg7cfftpe.us-east-1.es.amazonaws.com'
region = 'us-east-1'

service = 'es'
credentials = boto3.Session().get_credentials()
#print(credentials.access_key, credentials.secret_key)
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, service, session_token=credentials.token)

client = OpenSearch(
    hosts = [{'host': HOST, 'port': 443}],
    http_auth = awsauth,
    use_ssl = True,
    verify_certs = True,
    connection_class = RequestsHttpConnection
)

print('Connection successful')

index = 'photos'
#create_indices(client)

rekognition = boto3.client('rekognition', region_name='us-east-1')

datatype = '_doc'
url = host + '/' + index +'/'+datatype

print('url',url)
    
def get_label(rek, bucket, key):
    return rek.detect_labels(
        Image={
            'S3Object': {
                'Bucket': bucket,
                'Name': key
            }
        }
        , MaxLabels=10)

def create_indices(client):
    index_body = {
      'settings': {
        'index': {
          'number_of_shards': 1
        }
      }
    }
    response = client.indices.create(index, body=index_body)
    print(response)
    print('Index creation successful')


def get_custom_labels(bucket, key):
    header = boto3.client('s3').head_object(Bucket=bucket, Key=key)
    http_headers = header['ResponseMetadata']['HTTPHeaders']
    #print('Header:',http_headers)
    if 'x-amz-meta-customlabels' in http_headers:
        labels = http_headers['x-amz-meta-customlabels']
        return labels.split(',')

    
def lambda_handler(event, context):
    print(json.dumps(event))
    
    for r in event['Records']:
        obj = r['s3']
        bucket_name = obj['bucket']['name']
        key = obj['object']['key']
        
        # access rekognition to get labels
        print(bucket_name, key)
        
        header = boto3.client('s3').head_object(Bucket=bucket_name, Key=key)
        print('Header:',header)
        
        out = get_label(rekognition, bucket_name, key)
        
        print('Rekognition:',out)
        
        custom_labels = get_custom_labels(bucket_name, key) #array
        print('Custom:', custom_labels)
        
        labels = []
        for label in out['Labels']:
            sing_label = inflection.singularize(label['Name']).lower()
            #print(sing_label)
            labels.append(sing_label)
        if(custom_labels != None):
            for label in custom_labels:
                sing_label = inflection.singularize(label).lower()
                if(sing_label not in labels):
                    labels.append(sing_label)
      
      
        '''
        entry = {}
        entry['objectKey'] = key
        entry['bucket'] = bucket_name
        entry['createdTimestamp'] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        entry['labels'] = labels
        '''

        
        entry = {
                'objectKey' : key,
                'bucket' : bucket_name,
                'createdTimestamp' : datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                'labels' : labels
                }
        
        
        print('entry:',entry)
        
        # post to photos es
        headers = { "Content-Type": "application/json" }
        url = 'https://search-photos2-iso42y4zytwc3luoezg7cfftpe.us-east-1.es.amazonaws.com/photos/_doc'
        req = requests.post(url, auth=awsauth, data=json.dumps(entry), headers=headers)
        #print("error reason:", req.text)
        print("Success: ", req, req.text)
        
    return {
        'statusCode': 200,
        'headers': {
            "Access-Control-Allow-Origin": "*",
            'Content-Type': 'application/json'
        },
        'body': json.dumps("index photos completed")
    }