#! /usr/bin/python3

import json
import logging
import os
import random
from datetime import datetime

from boto3 import client
from python.opentelemetry import trace
from python.opentelemetry.trace import StatusCode
from python.pythonjsonlogger import jsonlogger

OTEL_SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME")
CUSTOM_OTEL_SPAN_EVENT_NAME = "LambdaCheckEvent"

# Reset logger
logger = logging.getLogger()
if logger.handlers:
    for handler in logger.handlers:
        logger.removeHandler(handler)

# Init logger
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)
logger.setLevel(level=logging.INFO)

client_s3 = client("s3")

random.seed(datetime.now().timestamp())


def log(level, msg, attrs={}):
    span = trace.get_current_span()
    span_context = span.get_span_context()
    if span_context.is_valid:
        attrs["service.name"] = OTEL_SERVICE_NAME
        attrs["trace.id"] = "{trace:032x}".format(trace=span_context.trace_id)
        attrs["span.id"] = "{span:016x}".format(span=span_context.span_id)

    logger.log(level=level, msg=msg, extra=attrs)


def parse_message(
    record,
):
    log(
        level=logging.INFO,
        msg="Parsing SQS message...",
    )

    message = json.loads(record["body"])
    bucket_name = message["bucket"]
    key_name = message["key"]
    correlation_id = record["messageAttributes"]["correlation-id"]["stringValue"]

    log(
        level=logging.INFO,
        msg="Parsing SQS message is succeeded.",
        attrs={
            "correlation.id": correlation_id,
            "bucket.name": bucket_name,
            "key.name": key_name,
        },
    )

    return correlation_id, bucket_name, key_name


def get_custom_object_from_s3(
    correlation_id,
    bucket_name,
    key_name,
):
    log(
        level=logging.INFO,
        msg="Getting custom object from the S3...",
        attrs={
            "correlation.id": correlation_id,
            "bucket.name": bucket_name,
            "key.name": key_name,
        },
    )

    try:
        custom_object = json.loads(
            client_s3.get_object(
                Bucket=bucket_name,
                Key=key_name,
            )["Body"].read()
        )

        log(
            level=logging.INFO,
            msg="Getting custom object from the S3 is succeeded.",
            attrs={
                "correlation.id": correlation_id,
                "bucket.name": bucket_name,
                "key.name": key_name,
            },
        )
        return custom_object

    except Exception as e:
        msg = "Getting custom object from the S3 is failed."
        log(
            level=logging.ERROR,
            msg=msg,
            attrs={
                "correlation.id": correlation_id,
                "bucket.name": bucket_name,
                "key.name": key_name,
                "error.message": str(e),
            },
        )
        raise Exception(msg)


def check_custom_object(
    custom_object,
):
    custom_object["isChecked"] = True


def cause_error():
    n = random.randint(0, 15)
    return n == 1


def store_custom_object_in_s3(
    correlation_id,
    bucket_name,
    key_name,
    custom_object,
):
    try:
        log(
            level=logging.INFO,
            msg="Checking custom object...",
            attrs={
                "correlation.id": correlation_id,
                "bucket.name": bucket_name,
                "key.name": key_name,
            },
        )

        if cause_error():
            key_name = "wrong-key-name"

        client_s3.put_object(
            Body=json.dumps(custom_object),
            Bucket=bucket_name,
            Key=key_name,
        )

        log(
            level=logging.INFO,
            msg="Checking custom object is succeeded.",
            attrs={
                "correlation.id": correlation_id,
                "bucket.name": bucket_name,
                "key.name": key_name,
            },
        )

    except Exception as e:
        msg = "Checking custom object is failed."
        log(
            level=logging.ERROR,
            msg=msg,
            attrs={
                "correlation.id": correlation_id,
                "bucket.name": bucket_name,
                "key.name": key_name,
                "error.message": str(e),
            },
        )
        raise Exception(msg)


def enrich_span_with_success(
    context,
    correlation_id,
    bucket_name,
    key_name,
):
    span = trace.get_current_span()
    span.set_attribute("correlation.id", correlation_id)

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
    correlation_id,
    e,
    bucket_name,
    key_name,
):
    span = trace.get_current_span()
    span.set_attribute("correlation.id", correlation_id)

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
        correlation_id, bucket_name, key_name = parse_message(record)

        try:
            # Create the custom object from input bucket
            custom_object = get_custom_object_from_s3(
                correlation_id, bucket_name, key_name
            )

            # Check custom object
            check_custom_object(custom_object)

            # Store the custom object in S3
            store_custom_object_in_s3(
                correlation_id, bucket_name, key_name, custom_object
            )

            # Enrich span with success
            enrich_span_with_success(context, correlation_id, bucket_name, key_name)

        except Exception as e:

            # Enrich span with failure
            enrich_span_with_failure(context, correlation_id, e, bucket_name, key_name)
