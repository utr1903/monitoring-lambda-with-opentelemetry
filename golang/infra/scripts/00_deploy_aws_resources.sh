#!/bin/bash

# Get commandline arguments
while (( "$#" )); do
  case "$1" in
    --destroy)
      flagDestroy="true"
      shift
      ;;
    --dry-run)
      flagDryRun="true"
      shift
      ;;
    *)
      shift
      ;;
  esac
done

### Build Go binaries
GOOS=linux GOARCH=amd64 CGO_ENABLED=0 go build -C ../../apps/create -o ../../apps/create/bin/main main.go

if [[ $flagDestroy != "true" ]]; then

  # Initialize Terraform
  terraform -chdir=../terraform init

  # Plan Terraform
  terraform -chdir=../terraform plan \
    -var AWS_REGION=$AWS_REGION \
    -var NEWRELIC_LICENSE_KEY=$NEWRELIC_LICENSE_KEY \
    -out "./tfplan"

  # Apply Terraform
  if [[ $flagDryRun != "true" ]]; then
    terraform -chdir=../terraform apply tfplan
  fi
else

  # Destroy Terraform
  terraform -chdir=../terraform destroy \
    -var AWS_REGION=$AWS_REGION \
    -var NEWRELIC_LICENSE_KEY=$NEWRELIC_LICENSE_KEY
fi
