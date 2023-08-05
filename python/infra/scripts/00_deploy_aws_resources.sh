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

### Set variables

if [[ $flagDestroy != "true" ]]; then

  # Install packages
  pip3 install -r "../../apps/create/requirements.txt" --target ../../apps/create/python
  pip3 install -r "../../apps/update/requirements.txt" --target ../../apps/update/python
  pip3 install -r "../../apps/delete/requirements.txt" --target ../../apps/delete/python
  pip3 install -r "../../apps/check/requirements.txt" --target ../../apps/check/python

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
