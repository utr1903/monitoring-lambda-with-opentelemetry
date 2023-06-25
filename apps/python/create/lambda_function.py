#! /usr/bin/python3

import os
import boto3
import json
import logging

logging.basicConfig(level = logging.INFO)
logger = logging.getLogger()

client = boto3.client('s3')

S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME')

def lambda_handler (event, context):

  logger.info(S3_BUCKET_NAME)

  test = {
    'test': 'test',
  }
  logger.info(test)

  client.put_object(
    Body=json.dumps(test),
    Bucket=S3_BUCKET_NAME,
    Key='test/test.json',
  )

  return {
    'statusCode': 200,
    'headers': {
      'Content-Type': 'application/ison'
    },
    'body': json.dumps(test),
  }
