# Monitoring Lambda with OpenTelemetry

This repository contains all of the instructions and files you need to instrument & monitor AWS Lambda functions with OpenTelemetry across several common programming languages. 

Throughout this lab, and across multiple scenarios you will use the basic data processing environment is built:

![Architecture](/docs/architecture.png)

## Requirements

- A free account with [New Relic](https://newrelic.com)


## Getting Started

1. From a new terminal window, clone this repository to your local machine using Git `git clone https://github.com/utr1903/monitoring-lambda-with-opentelemetry.git`
2. Navigate into your new workspace using `cd monitoring-lambda-with-opentelemetry`
3. Move onto the first lab of this workshop

- Lab 1: [Lab Name]()
- Lab 2: [Lab Name]()

## Workflow

### Create

A simulator is invoking the `create` Lambda function per an API Gateway. This function is responsible for creating a custom object with the following properties:

```json
{
  "item": "test",
  "isUpdated": false,
  "isChecked": false
}
```

It will then store this custom object into the input S3 bucket.

### Update

When the `create` Lambda stores the custom object into the input S3 bucket, the `update` Lambda will be triggered which

- gets the custom object from the input S3 bucket
- updates the custom object field `isUpdated` to true
  - ```json
    {
      "item": "test",
      "isUpdated": true,
      "isChecked": false
    }
    ```
- stores the updated custom object into the output S3 bucket
- sends the following message to SQS
  - ```json
    {
      "bucket": $OUTPUT_S3_BUCKET_NAME,
      "key": $UPDATED_CUSTOM_OBJECT_S3_KEY_NAME,
    }
    ```

### Check

The `check` Lambda consumes the messages published to the SQS and thereby the messages from the `update` Lambda where it

- parses the `bucket` and `key` from the message
- gets the custom object from that bucket
- marks it checked by setting the field `isChecked` to true as follows:
  - ```json
    {
      "item": "test",
      "isUpdated": true,
      "isChecked": true
    }
    ```
- stores it back to the bucket

### Delete

The `delete` Lambda is independent from the rest of the Lambdas. It is a cron job which deletes all of the objects in the input S3 bucket every minute. It

- gets all of the object info from the input S3 bucket
- deletes all of the objects in the input S3 bucket

## Instrumentation

The instrumentation of each service in each programming language consist of auto and manual instrumentation.

- The Lambdas are wrapped with Open Telemetry auto-instrumentation layers which instruments the inbound & outbound calls to/from your applications.
- In order to track custom KPIs, the manual instrumentation comes into play. For example, creating custom span events or adding additional attributes to some spans.

The generated telemetry data within the Lambda is then flushed to an Open Telemetry collector which is mounted to the Lambda either as a zip package or a layer (see code). The collector is then responsible to forward the telemetry data to your backend of choice!

**REMARK:** Currently the code is designed to send data to [New Relic](https://newrelic.com/) by default. Feel free to change the OTel collector config and Terraform Lambda environment variables to send data to elsewhere.

## Deployment

As prerequisites, you need

- Terraform (required)
- Configured AWS CLI (required)
- Go >1.18 SDK (only required for Golang)
- Maven >3 (only required for Java)
- Java >11 SDK (only required for Java)

Currently, every programming language has its own environment:

- [Golang](/golang/)
- [Java](/java/)
- [Python](/python/)

The folder structure of each language is the same:

```
- apps
  - check
  - create
  - delete
  - update
- infra
  - scripts
  - terraform
```

First, set the following environment variables:

- `AWS_REGION`
- `NEWRELIC_LICENSE_KEY`

Next to deploy everything, switch to the `{language}/infra/scripts` directory and simply run:

```bash
bash 00_deploy_aws_resources.sh
```

**REMARK:** To deploy the Python environment, you do not need to have the Python runtime installed in your machine. However for Golang and Java, you do need necessary SDKs (see prerequisites).

After the Terraform deployment is complete, the public URL of the API Gateway will be prompted to your terminal. You can generate some traffic by triggering it with the following `one-line curl loop`:

```bash
while true; do; curl -X POST "${API_GATEWAY_PUBLIC_URL}/create"; sleep 1; done
```

Example:

```bash
while true; do; curl -X POST "https://mmzght1j5l.execute-api.eu-west-1.amazonaws.com/prod/create"; sleep 1; done
```

## Capability Matrix

In every cell:

- 1st mark is for the implementation of the code
- 2nd mark is for the implementation of the auto-instrumentation
- 3rd mark is for the implementation of the manual-instrumentation

| Language | create   | update   | check    | delete   |
| -------- | -------- | -------- | -------- | -------- |
| Golang   | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| Java     | ✅ ✅ ✅ | ✅ ❌ ❌ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| Python   | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |

### Golang

- The trace context propagation between Lambdas fails to be established due to lack of SDK functionality.

### Java

- The `update` Lambda cannot be instrumented currently because of the [bug](https://github.com/open-telemetry/opentelemetry-lambda/issues/640).

## TODOs

- Send metrics
- Send logs (in context with traces)
