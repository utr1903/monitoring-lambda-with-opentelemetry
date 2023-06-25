#! /usr/bin/python3

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

  s3BucketName = event['Records'][0]['s3']['bucket']['name']
  s3BucketKey = event['Records'][0]['s3']['object']['key']
  
  logger.info(s3BucketName)
  logger.info(s3BucketKey)

  item = json.loads(
    client.get_object(
      Bucket=s3BucketName,
      Key=s3BucketKey,
    )['Body'].read())

  logger.info(item)

  item['isValid'] = True

  client.put_object(
    Body=json.dumps(item),
    Bucket=s3BucketName,
    Key=s3BucketKey,
  )
