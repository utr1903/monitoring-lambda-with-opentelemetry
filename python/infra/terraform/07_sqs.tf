###########
### SQS ###
###########

# SQS queue
resource "aws_sqs_queue" "queue" {
  name                        = local.sqs_queue_name
  fifo_queue                  = true
  content_based_deduplication = true
}
