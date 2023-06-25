#! /usr/bin/python3

import os
import boto3
import json
import logging
from datetime import datetime

logging.basicConfig(level = logging.INFO)
logger = logging.getLogger()

client = boto3.client('s3')

S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME')

def lambda_handler (event, context):

  logger.info(S3_BUCKET_NAME)

  item = {
    'item': 'test',
    'isValid': False,
  }
  logger.info(item)

  now = datetime.today().isoformat()

  client.put_object(
    Body=json.dumps(item),
    Bucket=S3_BUCKET_NAME,
    Key=f'items/{now}.json',
  )

  return {
    'statusCode': 200,
    'headers': {
      'Content-Type': 'application/ison'
    },
    'body': json.dumps(item),
  }
