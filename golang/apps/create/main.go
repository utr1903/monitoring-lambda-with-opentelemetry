package main

import (
	"github.com/aws/aws-lambda-go/events"
	"github.com/aws/aws-lambda-go/lambda"
)

type MyEvent struct {
	Name string `json:"name"`
}

func main() {
	lambda.Start(HandleRequest)
}

func HandleRequest(
	req events.APIGatewayProxyRequest,
) (
	events.APIGatewayProxyResponse,
	error,
) {
	res := events.APIGatewayProxyResponse{
		StatusCode: 200,
		Body:       "Hello",
	}

	return res, nil
}
