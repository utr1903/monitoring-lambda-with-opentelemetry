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

clientS3 = boto3.client('s3')
clientSqs = boto3.client("sqs")

OUTPUT_S3_BUCKET_NAME = os.getenv('OUTPUT_S3_BUCKET_NAME')
SQS_QUEUE_URL = os.getenv('SQS_QUEUE_URL')

def lambda_handler (event, context):

  # Parse
  s3BucketName = event['Records'][0]['s3']['bucket']['name']
  s3BucketKey = event['Records'][0]['s3']['object']['key']

  # Retrieve
  logger.info('Retrieving item from S3...')

  item = json.loads(
    clientS3.get_object(
      Bucket=s3BucketName,
      Key=s3BucketKey,
    )['Body'].read())
  
  logger.info('Item is retrieved from S3.')

  # Update
  logger.info('Updating item in S3...')

  item['isUpdated'] = True
  clientS3.put_object(
    Body=json.dumps(item),
    Bucket=OUTPUT_S3_BUCKET_NAME,
    Key=s3BucketKey,
  )

  logger.info('Item in S3 is updated.')

  # Send
  logger.info('Sending message to SQS...')

  message = {
    'bucket': s3BucketName,
    'key': s3BucketKey,
  }

  response = clientSqs.send_message(
      QueueUrl=SQS_QUEUE_URL,
      MessageBody=json.dumps(message)
  )

  logger.info(response)
  logger.info('Message is sent to SQS.')
