#! /usr/bin/python3

import os
import boto3
import json
import logging
from datetime import datetime

# Reset and init logger
logger = logging.getLogger()
if logger.handlers:
    for handler in logger.handlers:
        logger.removeHandler(handler)
logging.basicConfig(level=logging.INFO)

client = boto3.client('s3')

S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME')

def lambda_handler (event, context):

  now = datetime.now().timestamp()
  logger.info(f'timestamp:{now}')

  item = {
    'item': 'test',
    'isValid': False,
  }

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
