#! /usr/bin/python3

import json
import logging
import random
from datetime import datetime

from python.boto3 import client
from python.opentelemetry import trace
from python.opentelemetry.trace import Status, StatusCode

CUSTOM_OTEL_SPAN_EVENT_NAME = "LambdaCheckEvent"

# Reset and init logger
logger = logging.getLogger()
if logger.handlers:
    for handler in logger.handlers:
        logger.removeHandler(handler)
logging.basicConfig(level=logging.INFO)

client_s3 = client("s3")

random.seed(datetime.now().timestamp())


def parse_message(
    record,
):
    logger.info("Parsing SQS message...")

    message = json.loads(record["body"])
    bucket_name = message["bucket"]
    key_name = message["key"]

    logger.info("Parsing SQS message is succeeded.")
    return bucket_name, key_name


def get_custom_object_from_s3(
    bucket_name,
    key_name,
):
    logger.info("Getting custom object from the S3...")

    try:
        custom_object = json.loads(
            client_s3.get_object(
                Bucket=bucket_name,
                Key=key_name,
            )["Body"].read()
        )

        logger.info("Getting custom object from the S3 is succeeded.")
        return custom_object

    except Exception as e:
        msg = f"Getting custom object from the S3 is failed: {str(e)}"
        logger.error(msg)
        raise Exception(msg)


def check_custom_object(
    custom_object,
):
    custom_object["isChecked"] = True


def cause_error():
    n = random.randint(0, 15)
    return n == 1


def store_custom_object_in_s3(
    bucket_name,
    key_name,
    custom_object,
):
    try:
        logger.info("Checking custom object...")

        if cause_error():
            key_name = "wrong-key-name"

        client_s3.put_object(
            Body=json.dumps(custom_object),
            Bucket=bucket_name,
            Key=key_name,
        )

        logger.info("Checking custom object is succeeded.")

    except Exception as e:
        msg = f"Checking custom object is failed: {str(e)}"
        logger.error(msg)
        raise Exception(msg)


def enrich_span_with_success(
    context,
    bucket_name,
    key_name,
):
    span = trace.get_current_span()

    span.add_event(
        CUSTOM_OTEL_SPAN_EVENT_NAME,
        attributes={
            "is.successful": True,
            "bucket.id": bucket_name,
            "key.name": key_name,
            "aws.request.id": context.aws_request_id,
        },
    )


def enrich_span_with_failure(
    context,
    e,
    bucket_name,
    key_name,
):
    span = trace.get_current_span()

    span.set_status(StatusCode.ERROR, "Check Lambda is failed.")
    span.record_exception(exception=e, escaped=True)

    span.add_event(
        CUSTOM_OTEL_SPAN_EVENT_NAME,
        attributes={
            "is.successful": False,
            "bucket.id": bucket_name,
            "key.name": key_name,
            "aws.request.id": context.aws_request_id,
        },
    )


def lambda_handler(event, context):

    for record in event["Records"]:

        # Parse SQS message
        bucket_name, key_name = parse_message(record)

        try:

            # Create the custom object from input bucket
            custom_object = get_custom_object_from_s3(bucket_name, key_name)

            # Check custom object
            check_custom_object(custom_object)

            # Store the custom object in S3
            store_custom_object_in_s3(bucket_name, key_name, custom_object)

            # Enrich span with success
            enrich_span_with_success(context, bucket_name, key_name)

        except Exception as e:

            # Enrich span with failure
            enrich_span_with_failure(context, e, bucket_name, key_name)
