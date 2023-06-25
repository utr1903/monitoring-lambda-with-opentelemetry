#! /usr/bin/python3

import os
import boto3
import logging
from datetime import datetime

# Reset and init logger
logger = logging.getLogger()
if logger.handlers:
    for handler in logger.handlers:
        logger.removeHandler(handler)
logging.basicConfig(level=logging.INFO)

s3 = boto3.resource('s3')

INPUT_S3_BUCKET_NAME = os.getenv('INPUT_S3_BUCKET_NAME')

def lambda_handler (event, context):

  logger.info('Deleting all objects...')

  bucket = s3.Bucket(INPUT_S3_BUCKET_NAME)
  bucket.objects.all().delete()

  logger.info('All objects are deleted.')
