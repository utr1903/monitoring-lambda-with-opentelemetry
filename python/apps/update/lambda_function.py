#! /usr/bin/python3

import os
import boto3
import json
import logging
import random
import traceback

from datetime import datetime
from python.opentelemetry import trace
from python.opentelemetry.semconv.trace import SpanAttributes

CUSTOM_OTEL_SPAN_EVENT_NAME = 'LambdaUpdateEvent'
SQS_MESSAGE_GROUP_ID = 'otel'

# Reset and init logger
logger = logging.getLogger()
if logger.handlers:
    for handler in logger.handlers:
        logger.removeHandler(handler)
logging.basicConfig(level=logging.INFO)

client_s3 = boto3.client('s3')
client_sqs = boto3.client('sqs')

random.seed(datetime.now().timestamp())

OUTPUT_S3_BUCKET_NAME = os.getenv('OUTPUT_S3_BUCKET_NAME')
SQS_QUEUE_URL = os.getenv('SQS_QUEUE_URL')


def cause_error():
    n = random.randint(0, 15)
    return n == 1


def get_custom_object_from_input_s3(
        bucket_name,
        key_name
):
    logger.info('Getting custom object from the input S3...')

    try:
        custom_object = json.loads(
            client_s3.get_object(
                Bucket=bucket_name,
                Key=key_name,
            )['Body'].read())

        logger.info('Getting custom object from the input S3 is succeeded.')
        return custom_object

    except Exception as e:
        msg = f'Getting custom object from the input S3 is failed: {str(e)}'
        logger.error(msg)
        raise Exception(msg)


def update_custom_object(
        custom_object,
):
    custom_object['isUpdated'] = True


def store_custom_object_in_output_s3(
        key_name,
        custom_object,
):
    try:
        logger.info('Updating custom object in the output S3...')

        bucket_name = f'{OUTPUT_S3_BUCKET_NAME}'
        if cause_error():
            bucket_name = 'wrong-bucket-name'

        client_s3.put_object(
            Bucket=bucket_name,
            Key=key_name,
            Body=json.dumps(custom_object),
        )

        logger.info('Updating custom object in output S3 is succeeded.')

    except Exception as e:
        msg = f'Updating custom object in the output S3 is failed: {str(e)}'
        logger.error(msg)
        raise Exception(msg)


def send_custom_object_s3_info_to_sqs(
        bucket_name,
        key_name,
):
    try:
        logger.info(
            'Sending S3 info of the updated custom object to SQS...')

        message = {
            'bucket': bucket_name,
            'key': key_name,
        }

        client_sqs.send_message(
            MessageGroupId=SQS_MESSAGE_GROUP_ID,
            QueueUrl=SQS_QUEUE_URL,
            MessageBody=json.dumps(message)
        )

        logger.info(
            'Sending S3 info of the updated custom object to SQS is succeeded.')

    except Exception as e:
        msg = f'Sending S3 info of the updated custom object to SQS is failed: {str(e)}'
        logger.error(msg)
        raise Exception(msg)


def enrich_span_with_success(
        context,
):
    span = trace.get_current_span()

    span.add_event(
        CUSTOM_OTEL_SPAN_EVENT_NAME,
        attributes={
            'is.successful': True,
            'aws.request.id': context.aws_request_id
        })


def enrich_span_with_failure(
    context,
    e,
):

    span = trace.get_current_span()

    span.set_attribute('otel.status_code', 'ERROR')
    span.set_attribute('otel.status_description', 'Update Lambda is failed.')
    span.set_attribute(SpanAttributes.EXCEPTION_TYPE, str(type(e)))
    span.set_attribute(SpanAttributes.EXCEPTION_MESSAGE, str(e))
    span.set_attribute(SpanAttributes.EXCEPTION_STACKTRACE,
                       traceback.format_exc())

    span.add_event(
        CUSTOM_OTEL_SPAN_EVENT_NAME,
        attributes={
            'is.successful': False,
            'aws.request.id': context.aws_request_id
        })


def lambda_handler(event, context):

    # Parse bucket information
    bucket_name = event['Records'][0]['s3']['bucket']['name']
    key_name = event['Records'][0]['s3']['object']['key']

    try:
        # Create the custom object from input bucket
        custom_object = get_custom_object_from_input_s3(bucket_name, key_name)

        # Update custom object
        update_custom_object(custom_object)

        # Store the custom object in S3
        store_custom_object_in_output_s3(key_name, custom_object)

        # Send custom object to SQS
        send_custom_object_s3_info_to_sqs(bucket_name, key_name)

        # Enrich span with success
        enrich_span_with_success(context)

    except Exception as e:

        # Enrich span with failure
        enrich_span_with_failure(context, e)
