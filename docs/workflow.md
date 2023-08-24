# Workflow

## Create (API Gateway triggered)

A simulator is invoking the `create` Lambda function per an API Gateway. This function is responsible for creating a custom object with the following properties:

```json
{
  "item": "test",
  "isUpdated": false,
  "isChecked": false
}
```

It will then store this custom object into the input S3 bucket.

## Update (S3 triggered)

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

## Check (SQS triggered)

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

## Delete (Event bridge triggered)

The `delete` Lambda is independent from the rest of the Lambdas. It is a cron job which deletes all of the objects in the input S3 bucket every minute. It

- gets all of the object information from the input S3 bucket
- deletes all of the objects in the input S3 bucket
