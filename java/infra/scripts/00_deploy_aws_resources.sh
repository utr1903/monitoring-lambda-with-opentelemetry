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

if [[ $flagDestroy != "true" ]]; then

  ### Build jar files
  mvn clean install package -f ../../apps/create/pom.xml
  mvn clean install package -f ../../apps/update/pom.xml
  mvn clean install package -f ../../apps/delete/pom.xml
  mvn clean install package -f ../../apps/check/pom.xml

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
