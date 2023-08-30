# Monitoring Lambda Functions with OpenTelemetry

This repository contains all of the instructions and files you need to instrument & monitor an AWS Lambda function with OpenTelemetry across several common programming languages. 

## Prerequisites
The following required software must be accessible from your command line:

- Terraform (required)
  - Check with `terraform --version`
  - [Installation docs](https://developer.hashicorp.com/terraform/downloads)
- Configured AWS CLI (required)
  - Check with `aws --version`
  - [Installation docs](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
  - [Configuration docs](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html)
  - [Configuration video](https://www.youtube.com/watch?v=Rp-A84oh4G8)
- Go `>1.18` SDK (only required for Golang)
  - Check with `go version`
  - [Installation docs](https://go.dev/doc/install)
- Maven `>3.x` (only required for Java)
  - Check with `mvn -v`
  - [Download docs](https://maven.apache.org/download.cgi)
  - [Installation docs](https://maven.apache.org/install.html)
- Java `>11` SDK (only required for Java)
  - Check with `java -version`
  - [Installation docs (Amazon Coretto 17)](https://docs.aws.amazon.com/corretto/latest/corretto-17-ug/what-is-corretto-17.html)
- Python `>3.10` (only required for Python)
  - Check with `python3 --version`
  - [Installation docs (3.11)](https://www.python.org/downloads/release/python-3110/)

## Architecture

In order to demonstrate different scenarios, a sample data processing environment has been build for this workshop. The structure of the environment can be seen in the inmage below:

![Architecture](/docs/architecture.png)

Refer to this [documentation](/docs/workflow.md) to learn more about what you will be deploying!

## Getting started

In a new terminal window, clone this repository and `cd` into it:

```
git clone https://github.com/utr1903/monitoring-lambda-with-opentelemetry
cd monitoring-lambda-with-opentelemetry
```

Currently, every programming language in this repo has its own environment:

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
<details>
 <summary><strong>Account Setup</strong></summary>

In this step, you will associate your [AWS region](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Concepts.RegionsAndAvailabilityZones.html) and [New Relic license key](https://docs.newrelic.com/docs/apis/intro-apis/new-relic-api-keys/#license-key) to the application so that telemetry data will be sent to your New Relic account. If you don't already have a New Relic account, set one up for free [here](https://newrelic.com/signup)

Next, set the environment variables with the following CLI commands:

```bash
export AWS_REGION="XXX" # example: eu-west-1
export NEWRELIC_LICENSE_KEY="XXX"
```
</details>

<details>
 <summary><strong>Deploy AWS Resources</strong></summary>

Now we will deploy the AWS resources using a preconfigured Terraform script in the Golang directory.

1. Switch to the `{language}/infra/scripts` directory using the command below:

```bash
cd golang/infra/scripts
```

Next, run the `00_deploy_aws_resources.sh` script:

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

At this point, you have deployed and instrumented the Golang service. To view this data in New Relic immediately run the following query in your account:

```bash
SELECT * FROM Span WHERE instrumentation.provider = 'opentelemetry'
```
After 5 minutes have passed since running the terraform script, navigate to **All Entities** in the New Relic platform and locate the service named `goland-lambda-delete-otel`

</details>
## Full Instrumentation

The full instrumentation of each service in each programming language contains components of auto and manual instrumentation.

- The Lambda functions included in this environment are wrapped with OpenTelemetry auto-instrumentation layers which instruments the inbound & outbound calls to/from your services.
- In order to track custom KPIs, additional instrumentation (known as manual instrumentation) is needed. For example, creating custom span events or adding additional attributes to individual spans.

The telemetry data generated within the Lambda function is then sent to an OpenTelemetry collector which is mounted to the Lambda either as a zip package or a layer (see code). The collector is then responsible to forward the telemetry data to your backend of choice!

**REMARK:** Currently this repo is designed to send data to [New Relic](https://newrelic.com/) by default. However, it is possible to make small edits to the OTel collector config and Terraform Lambda environment variables to send data to elsewhere.

## Capability Matrix

The table below visualizes the level of instrumentation required for each service.

In each cell:

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
