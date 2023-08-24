# Monitoring Lambda with Open Telemetry

This repo is dedicated to show how to instrument & monitor AWS Lambda functions written in different programming languages with Open Telemetry.

## Prerequisites

- Terraform (required)
  - [Installation docs](https://developer.hashicorp.com/terraform/downloads)
- Configured AWS CLI (required)
  - [Installation docs](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
  - [Configuration docs](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html)
  - [Configuration video](https://www.youtube.com/watch?v=Rp-A84oh4G8)
- Go `>1.18` SDK (only required for Golang)
  - [Installation docs](https://go.dev/doc/install)
- Maven `>3.x` (only required for Java)
  - [Download docs](https://maven.apache.org/download.cgi)
  - [Installation docs](https://maven.apache.org/install.html)
- Java `>11` SDK (only required for Java)
  - [Installation docs (Amazon Coretto 17)](https://docs.aws.amazon.com/corretto/latest/corretto-17-ug/what-is-corretto-17.html)
- Python `>3.10` (only required for Python)
  - [Installation docs (3.11)](https://www.python.org/downloads/release/python-3110/)

## Architecture

In order to demonstrate different scenarios the following simple data processing environment is built:

![Architecture](/docs/architecture.png)

Refer to this [documentation](/docs/workflow.md) to learn more about what you will be deploying!

## Getting started

Open up a new terminal window, clone this repository and `cd` into it:

```
git clone https://github.com/utr1903/monitoring-lambda-with-opentelemetry
cd monitoring-lambda-with-opentelemetry
```

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

```bash
export AWS_REGION="XXX" # example: eu-west-1
export NEWRELIC_LICENSE_KEY="XXX"
```

Next, switch to the `{language}/infra/scripts` directory. For example:

```bash
cd golang/infra/scripts
```

Finally, run the `00_deploy_aws_resources.sh` script:

```bash
bash 00_deploy_aws_resources.sh
```

After the Terraform deployment is complete, the public URL of the API Gateway will be prompted to your terminal. You can generate some traffic by triggering it with the following `one-line curl loop`:

```bash
while true; do; curl -X POST "${API_GATEWAY_PUBLIC_URL}/create"; sleep 1; done
```

Example:

```bash
while true; do; curl -X POST "https://mmzght1j5l.execute-api.eu-west-1.amazonaws.com/prod/create"; sleep 1; done
```

## Instrumentation

The instrumentation of each service in each programming language consist of auto and manual instrumentation.

- The Lambdas are wrapped with Open Telemetry auto-instrumentation layers which instruments the inbound & outbound calls to/from your applications.
- In order to track custom KPIs, the manual instrumentation comes into play. For example, creating custom span events or adding additional attributes to some spans.

The generated telemetry data within the Lambda is then flushed to an Open Telemetry collector which is mounted to the Lambda either as a zip package or a layer (see code). The collector is then responsible to forward the telemetry data to your backend of choice!

**REMARK:** Currently the code is designed to send data to [New Relic](https://newrelic.com/) by default. Feel free to change the OTel collector config and Terraform Lambda environment variables to send data to elsewhere.

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

- The `update` Lambda cannot be auto-instrumented currently because of the [bug](https://github.com/open-telemetry/opentelemetry-lambda/issues/640).

## TODOs

- Propagate trace context
- Send metrics
- Send logs (in context with traces)
