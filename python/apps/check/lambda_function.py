#! /usr/bin/python3

import os
import boto3
import json
import logging

# Reset and init logger
logger = logging.getLogger()
if logger.handlers:
    for handler in logger.handlers:
        logger.removeHandler(handler)
logging.basicConfig(level=logging.INFO)

client = boto3.client('s3')

def lambda_handler (event, context):

  logger.info(json.dumps(event))

  for record in event['Records']:

    # Parse
    logger.info('Parsing message...')

    message = json.loads(record['body'])
    s3BucketName = message['bucket']
    s3BucketKey = message['key']

    logger.info('Message is parsed.')

    # Retrieve
    logger.info('Retrieving item from S3...')
    
    item = json.loads(
      client.get_object(
        Bucket=s3BucketName,
        Key=s3BucketKey,
      )['Body'].read())

    logger.info('Item is retrieved from S3.')

    # Check
    logger.info('Checking item in S3...')

    item['isChecked'] = True

    client.put_object(
      Body=json.dumps(item),
      Bucket=s3BucketName,
      Key=s3BucketKey,
    )

    logger.info('Item in S3 is checked.')
