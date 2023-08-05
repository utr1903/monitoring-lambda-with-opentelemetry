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

CUSTOM_OTEL_SPAN_EVENT_NAME = 'LambdaCreateEvent'

# Reset and init logger
logger = logging.getLogger()
if logger.handlers:
    for handler in logger.handlers:
        logger.removeHandler(handler)
logging.basicConfig(level=logging.INFO)

client_s3 = boto3.client('s3')

random.seed(datetime.now().timestamp())

INPUT_S3_BUCKET_NAME = os.getenv('INPUT_S3_BUCKET_NAME')


def create_custom_object():
    return {
        'item': 'test',
        'isUpdated': False,
        'isChecked': False,
    }


def cause_error():
    n = random.randint(0, 15)
    return n == 1


def store_custom_object_in_s3(
    body,
):
    logger.info('Storing custom object into S3...')

    bucket_name = f'{INPUT_S3_BUCKET_NAME}'
    if cause_error():
        bucket_name = 'wrong-bucket-name'

    try:
        client_s3.put_object(
            Bucket=bucket_name,
            Key=f'{datetime.now().timestamp()}',
            Body=json.dumps(body),
        )

        logger.info('Storing custom object into S3 is succeeded.')

    except Exception as e:
        msg = f'Storing custom object into S3 is failed: {str(e)}'
        logger.error(msg)
        raise Exception(msg)


def enrich_span_with_success(
        context
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
    span.set_attribute('otel.status_description', 'Create Lambda is failed.')
    span.set_attribute(SpanAttributes.EXCEPTION_TYPE, str(type(e)))
    span.set_attribute(SpanAttributes.EXCEPTION_MESSAGE, str(e))
    span.set_attribute(SpanAttributes.EXCEPTION_STACKTRACE,
                       traceback.format_exc())

    span.add_event(
        CUSTOM_OTEL_SPAN_EVENT_NAME,
        attributes={
            'is.successful': False,
            'bucket.id': INPUT_S3_BUCKET_NAME,
            'aws.request.id': context.aws_request_id
        })


def create_response(
        status_code,
        body,
):
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/ison'
        },
        'body': json.dumps(body),
    }


def lambda_handler(event, context):

    try:

        # Create custom object
        custom_object = create_custom_object()

        # Store the custom object in S3
        store_custom_object_in_s3(custom_object)

        # Enrich span with success
        enrich_span_with_success(context)

        return create_response(200, json.dumps(custom_object))
    except Exception as e:

        # Enrich span with failure
        enrich_span_with_failure(context, e)

        return create_response(200, json.dumps(custom_object))
