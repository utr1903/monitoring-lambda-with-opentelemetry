#! /usr/bin/python3

import os
import boto3
import logging

# Reset and init logger
logger = logging.getLogger()
if logger.handlers:
    for handler in logger.handlers:
        logger.removeHandler(handler)
logging.basicConfig(level=logging.INFO)

s3 = boto3.resource('s3')

INPUT_S3_BUCKET_NAME = os.getenv('INPUT_S3_BUCKET_NAME')
OUTPUT_S3_BUCKET_NAME = os.getenv('OUTPUT_S3_BUCKET_NAME')

def lambda_handler (event, context):

  logger.info('Deleting all objects in input bucket...')

  inputBucket = s3.Bucket(INPUT_S3_BUCKET_NAME)
  inputBucket.objects.all().delete()

  logger.info('All objects in input bucket are deleted.')

  logger.info('Deleting all objects in output bucket...')

  outputBucket = s3.Bucket(OUTPUT_S3_BUCKET_NAME)
  outputBucket.objects.all().delete()

  logger.info('All objects in output bucket are deleted.')
