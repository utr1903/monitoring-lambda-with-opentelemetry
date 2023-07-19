###########
### SQS ###
###########

# SQS queue
resource "aws_sqs_queue" "python_queue" {
  name                        = local.python_sqs_queue_name
  fifo_queue                  = true
  content_based_deduplication = true
}
