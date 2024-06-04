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
CUSTOM_OTEL_SPAN_EVENT_NAME = "LambdaUpdateEvent"
SQS_MESSAGE_GROUP_ID = "otel"


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
client_sqs = client("sqs")

random.seed(datetime.now().timestamp())

OUTPUT_S3_BUCKET_NAME = os.getenv("OUTPUT_S3_BUCKET_NAME")
SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL")


def log(level, msg, attrs={}):
    span = trace.get_current_span()
    span_context = span.get_span_context()
    if span_context.is_valid:
        attrs["service.name"] = OTEL_SERVICE_NAME
        attrs["trace.id"] = "{trace:032x}".format(trace=span_context.trace_id)
        attrs["span.id"] = "{span:016x}".format(span=span_context.span_id)

    logger.log(level=level, msg=msg, extra=attrs)


def cause_error():
    n = random.randint(0, 15)
    return n == 1


def get_custom_object_from_input_s3(
    bucket_name,
    key_name,
):
    log(
        level=logging.INFO,
        msg="Getting custom object from the input S3...",
        attrs={
            "bucket.name": bucket_name,
            "key.name": key_name,
        },
    )

    try:
        obj = client_s3.get_object(
            Bucket=bucket_name,
            Key=key_name,
        )

        custom_object_body = json.loads(obj["Body"].read())
        correlation_id = obj["Metadata"]["correlation-id"]

        log(
            level=logging.INFO,
            msg="Getting custom object from the input S3 is succeeded.",
            attrs={
                "correlation.id": correlation_id,
                "bucket.name": bucket_name,
                "key.name": key_name,
            },
        )
        return correlation_id, custom_object_body

    except Exception as e:
        msg = "Getting custom object from the input S3 is failed."
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


def update_custom_object(
    custom_object,
):
    custom_object["isUpdated"] = True


def store_custom_object_in_output_s3(
    correlation_id,
    key_name,
    custom_object,
):
    try:
        bucket_name = f"{OUTPUT_S3_BUCKET_NAME}"
        if cause_error():
            bucket_name = "wrong-bucket-name"

        log(
            level=logging.INFO,
            msg="Updating custom object in the output S3...",
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

        client_s3.put_object(
            Bucket=bucket_name,
            Key=key_name,
            Body=json.dumps(custom_object),
            Metadata={
                "correlation-id": correlation_id,
            },
        )

        log(
            level=logging.INFO,
            msg="Updating custom object in output S3 is succeeded.",
            attrs={
                "correlation.id": correlation_id,
                "bucket.name": bucket_name,
                "key.name": key_name,
            },
        )

    except Exception as e:
        msg = "Updating custom object in the output S3 is failed."
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


def send_custom_object_s3_info_to_sqs(
    correlation_id,
    key_name,
):
    try:
        log(
            level=logging.INFO,
            msg="Sending S3 info of the updated custom object to SQS...",
            attrs={
                "correlation.id": correlation_id,
                "bucket.name": OUTPUT_S3_BUCKET_NAME,
                "key.name": key_name,
            },
        )

        message = {
            "bucket": OUTPUT_S3_BUCKET_NAME,
            "key": key_name,
        }

        # Create message attributes
        msg_attrs = {
            "correlation-id": {
                "DataType": "String",
                "StringValue": correlation_id,
            }
        }

        client_sqs.send_message(
            MessageGroupId=SQS_MESSAGE_GROUP_ID,
            QueueUrl=SQS_QUEUE_URL,
            MessageBody=json.dumps(message),
            MessageAttributes=msg_attrs,
        )

        log(
            level=logging.INFO,
            msg="Sending S3 info of the updated custom object to SQS is succeeded.",
            attrs={
                "correlation.id": correlation_id,
                "bucket.name": OUTPUT_S3_BUCKET_NAME,
                "key.name": key_name,
            },
        )

    except Exception as e:
        msg = "Sending S3 info of the updated custom object to SQS is failed."
        log(
            level=logging.ERROR,
            msg=msg,
            attrs={
                "correlation.id": correlation_id,
                "bucket.name": OUTPUT_S3_BUCKET_NAME,
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
        attributes={"is.successful": True, "aws.request.id": context.aws_request_id},
    )


def enrich_span_with_failure(
    context,
    correlation_id,
    e,
):
    span = trace.get_current_span()
    span.set_attribute("correlation.id", correlation_id)

    span.set_status(StatusCode.ERROR, "Update Lambda is failed.")
    span.record_exception(exception=e, escaped=True)

    span.add_event(
        CUSTOM_OTEL_SPAN_EVENT_NAME,
        attributes={"is.successful": False, "aws.request.id": context.aws_request_id},
    )


def lambda_handler(event, context):

    correlation_id = ""

    # Parse bucket information
    bucket_name = event["Records"][0]["s3"]["bucket"]["name"]
    key_name = event["Records"][0]["s3"]["object"]["key"]

    try:
        # Create the custom object from input bucket
        correlation_id, custom_object = get_custom_object_from_input_s3(
            bucket_name, key_name
        )

        # Update custom object
        update_custom_object(custom_object)

        # Store the custom object in S3
        store_custom_object_in_output_s3(correlation_id, key_name, custom_object)

        # Send custom object to SQS
        send_custom_object_s3_info_to_sqs(correlation_id, key_name)

        # Enrich span with success
        enrich_span_with_success(context, correlation_id)

    except Exception as e:

        # Enrich span with failure
        enrich_span_with_failure(context, correlation_id, e)
