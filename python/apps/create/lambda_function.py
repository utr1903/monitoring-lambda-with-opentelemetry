#! /usr/bin/python3

import json
import logging
import os
import random
import uuid
from datetime import datetime

from boto3 import client
from python.opentelemetry import trace
from python.opentelemetry.trace import StatusCode
from python.pythonjsonlogger import jsonlogger

CUSTOM_OTEL_SPAN_EVENT_NAME = "LambdaCreateEvent"

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

OTEL_SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME")
INPUT_S3_BUCKET_NAME = os.getenv("INPUT_S3_BUCKET_NAME")


def log(level, msg, attrs={}):
    span = trace.get_current_span()
    span_context = span.get_span_context()
    if span_context.is_valid:
        attrs["service.name"] = OTEL_SERVICE_NAME
        attrs["trace.id"] = "{trace:032x}".format(trace=span_context.trace_id)
        attrs["span.id"] = "{span:016x}".format(span=span_context.span_id)

    logger.log(level=level, msg=msg, extra=attrs)


def create_custom_object():
    return {
        "item": "test",
        "isUpdated": False,
        "isChecked": False,
    }


def cause_error():
    n = random.randint(0, 15)
    return n == 1


def store_custom_object_in_s3(
    correlation_id,
    body,
):
    bucket_name = f"{INPUT_S3_BUCKET_NAME}"
    if cause_error():
        bucket_name = "wrong-bucket-name"

    # Generate key name
    key_name = str(uuid.uuid4())

    log(
        level=logging.INFO,
        msg="Storing custom object into S3...",
        attrs={
            "correlation.id": correlation_id,
            "bucket.name": bucket_name,
            "key.name": key_name,
        },
    )

    # Add bucket and key name as attributes
    span = trace.get_current_span()
    span.set_attribute("bucket.name", bucket_name)
    span.set_attribute("key.name", key_name)

    try:
        client_s3.put_object(
            Bucket=bucket_name,
            Key=key_name,
            Body=json.dumps(body),
            Metadata={
                "correlation-id": correlation_id,
            },
        )

        log(
            level=logging.INFO,
            msg="Storing custom object into S3 is succeeded.",
            attrs={
                "correlation.id": correlation_id,
                "bucket.name": bucket_name,
                "key.name": key_name,
            },
        )

    except Exception as e:
        msg = "Storing custom object into S3 is failed."
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
):
    span = trace.get_current_span()
    span.set_attribute("correlation.id", correlation_id)

    span.add_event(
        CUSTOM_OTEL_SPAN_EVENT_NAME,
        attributes={
            "is.successful": True,
            "bucket.id": INPUT_S3_BUCKET_NAME,
            "aws.request.id": context.aws_request_id,
        },
    )


def enrich_span_with_failure(
    context,
    correlation_id,
    e,
):
    span = trace.get_current_span()
    span.set_attribute("correlation.id", correlation_id)

    span.set_status(StatusCode.ERROR, "Create Lambda is failed.")
    span.record_exception(exception=e, escaped=True)

    span.add_event(
        CUSTOM_OTEL_SPAN_EVENT_NAME,
        attributes={
            "is.successful": False,
            "bucket.id": INPUT_S3_BUCKET_NAME,
            "aws.request.id": context.aws_request_id,
        },
    )


def create_response(
    status_code,
    body,
):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/ison"},
        "body": json.dumps(body),
    }


def lambda_handler(event, context):

    # Generate correlation ID
    correlation_id = str(uuid.uuid4())

    try:

        # Create custom object
        custom_object = create_custom_object()

        # Store the custom object in S3
        store_custom_object_in_s3(correlation_id, custom_object)

        # Enrich span with success
        enrich_span_with_success(context, correlation_id)

        return create_response(200, json.dumps(custom_object))
    except Exception as e:

        # Enrich span with failure
        enrich_span_with_failure(context, correlation_id, e)

        return create_response(500, json.dumps(custom_object))
