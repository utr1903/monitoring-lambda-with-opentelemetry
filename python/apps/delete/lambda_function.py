#! /usr/bin/python3

import os
import boto3
import logging
import random
import traceback

from datetime import datetime
from python.opentelemetry import trace
from python.opentelemetry.semconv.trace import SpanAttributes

CUSTOM_OTEL_SPAN_EVENT_NAME = 'LambdaDeleteEvent'

# Reset and init logger
logger = logging.getLogger()
if logger.handlers:
    for handler in logger.handlers:
        logger.removeHandler(handler)
logging.basicConfig(level=logging.INFO)

client_s3 = boto3.resource('s3')

random.seed(datetime.now().timestamp())

INPUT_S3_BUCKET_NAME = os.getenv('INPUT_S3_BUCKET_NAME')


def cause_error():
    n = random.randint(0, 3)
    return n == 1


def get_all_custom_objects_in_input_s3():
    logger.info('Getting all custom objects in the input S3...')

    try:
        bucket_name = f'{INPUT_S3_BUCKET_NAME}'
        if cause_error():
            bucket_name = 'wrong-bucket-name'

        all_custom_objects = client_s3.Bucket(bucket_name).objects.all()

        logger.info('Getting all custom objects in the input S3 is succeeded.')
        return all_custom_objects

    except Exception as e:
        msg = f'Getting all custom objects in the input S3 is failed: {str(e)}'
        logger.error(msg)
        raise Exception(msg)


def delete_all_custom_objects_in_input_s3(
        all_custom_objects,
):
    logger.info('Deleting all custom objects in the input S3...')
    all_custom_objects.delete()
    logger.info('Deleting all custom objects in the input S3 is succeeded.')


def enrich_span_with_success(
        context,
):
    span = trace.get_current_span()

    span.add_event(
        CUSTOM_OTEL_SPAN_EVENT_NAME,
        attributes={
            'is.successful': True,
            'bucket.id': INPUT_S3_BUCKET_NAME,
            'aws.request.id': context.aws_request_id
        })


def enrich_span_with_failure(
    context,
    e,
):

    span = trace.get_current_span()

    span.set_attribute('otel.status_code', 'ERROR')
    span.set_attribute('otel.status_description', 'Delete Lambda is failed.')

    span.record_exception(exception=e, escaped=True)

    span.add_event(
        CUSTOM_OTEL_SPAN_EVENT_NAME,
        attributes={
            'is.successful': False,
            'bucket.id': INPUT_S3_BUCKET_NAME,
            'aws.request.id': context.aws_request_id
        })


def lambda_handler(event, context):

    try:
        # Get all custom objects in input bucket
        all_custom_objects = get_all_custom_objects_in_input_s3()

        # Delete the custom objects in input bucket
        delete_all_custom_objects_in_input_s3(all_custom_objects)

        # Enrich span with success
        enrich_span_with_success(context)

    except Exception as e:

        # Enrich span with failure
        enrich_span_with_failure(context, e)
