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

INPUT_S3_BUCKET_NAME = os.getenv('INPUT_S3_BUCKET_NAME')

def lambda_handler (event, context):

  now = datetime.now().timestamp()
  logger.info(f'timestamp:{now}')

  item = {
    'item': 'test',
    'isUpdated': False,
    'isChecked': False,
  }

  client.put_object(
    Body=json.dumps(item),
    Bucket=INPUT_S3_BUCKET_NAME,
    Key=f'items/{now}.json',
  )

  return {
    'statusCode': 200,
    'headers': {
      'Content-Type': 'application/ison'
    },
    'body': json.dumps(item),
  }
