package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"math/rand"
	"os"
	"strconv"
	"strings"
	"time"

	"github.com/aws/aws-lambda-go/events"
	"github.com/aws/aws-lambda-go/lambda"
	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/s3/s3manager"
	"go.opentelemetry.io/contrib/instrumentation/github.com/aws/aws-lambda-go/otellambda"
	"go.opentelemetry.io/contrib/instrumentation/github.com/aws/aws-lambda-go/otellambda/xrayconfig"
	"go.opentelemetry.io/contrib/propagators/aws/xray"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	semconv "go.opentelemetry.io/otel/semconv/v1.17.0"
	"go.opentelemetry.io/otel/trace"
)

const CUSTOM_OTEL_SPAN_EVENT_NAME = "LambdaCreateEvent"

var (
	randomizer           = rand.New(rand.NewSource(time.Now().UnixNano()))
	OTEL_SERVICE_NAME    string
	INPUT_S3_BUCKET_NAME string
	uploader             *s3manager.Uploader
)

type CustomObject struct {
	Item      string `json:"item"`
	IsUpdated bool   `json:"isUpdated"`
	IsChecked bool   `json:"isChecked"`
}

func main() {

	// Parse environment variables
	OTEL_SERVICE_NAME = os.Getenv("OTEL_SERVICE_NAME")
	INPUT_S3_BUCKET_NAME = os.Getenv("INPUT_S3_BUCKET_NAME")

	// Create a s3 uploader
	uploader = s3manager.NewUploader(session.Must(session.NewSession()))

	// Get context
	ctx := context.Background()

	// Create tracer provider
	tp, err := xrayconfig.NewTracerProvider(ctx)
	if err != nil {
		fmt.Printf("error creating tracer provider: %v", err)
	}

	defer func(ctx context.Context) {
		err := tp.Shutdown(ctx)
		if err != nil {
			fmt.Printf("error shutting down tracer provider: %v", err)
		}
	}(ctx)

	// Set global tracer provider
	otel.SetTracerProvider(tp)

	// Set propagator
	otel.SetTextMapPropagator(xray.Propagator{})

	// Wrap handler & instrument
	lambda.Start(otellambda.InstrumentHandler(handler, xrayconfig.WithRecommendedOptions(tp)...))
}

func handler(
	req events.APIGatewayProxyRequest,
) (
	events.APIGatewayProxyResponse,
	error,
) {

	// Start parent span
	ctx, parentSpan := startParentSpan(req)
	defer parentSpan.End()

	// Create object
	customObject := &CustomObject{
		Item:      "test",
		IsUpdated: false,
		IsChecked: false,
	}

	// Convert updated custom object to bytes
	customObjectAsBytes, err := convertCustomObjectIntoBytes(parentSpan, customObject)
	if err != nil {
		return events.APIGatewayProxyResponse{
			StatusCode: 500,
			Body:       "Failed",
		}, nil
	}

	// Store object in S3
	err = storeObjectInS3(ctx, parentSpan, customObjectAsBytes)
	if err != nil {

		parentSpan.SetAttributes([]attribute.KeyValue{
			semconv.HTTPStatusCode(500),
		}...)

		enrichSpanWithEvent(parentSpan, false)

		return events.APIGatewayProxyResponse{
			StatusCode: 500,
			Body:       "Failed",
		}, nil
	}

	parentSpan.SetAttributes([]attribute.KeyValue{
		semconv.HTTPStatusCode(200),
	}...)

	enrichSpanWithEvent(parentSpan, true)

	return events.APIGatewayProxyResponse{
		StatusCode: 200,
		Body:       string(customObjectAsBytes),
	}, nil
}

func startParentSpan(
	req events.APIGatewayProxyRequest,
) (
	context.Context,
	trace.Span,
) {
	// Create tracer
	tracer := otel.Tracer(OTEL_SERVICE_NAME)

	// Get context
	ctx := context.Background()

	// Start parent span
	return tracer.Start(ctx, "main.handler",
		trace.WithSpanKind(trace.SpanKindServer),
		trace.WithAttributes([]attribute.KeyValue{
			semconv.FaaSTriggerHTTP,
			semconv.NetTransportTCP,
			semconv.HTTPMethod(req.HTTPMethod),
			semconv.HTTPFlavorKey.String(req.RequestContext.Protocol),
			semconv.HTTPRoute(req.Resource),
			semconv.HTTPTarget(req.Resource),
			semconv.HTTPScheme(req.Headers["X-Forwarded-Proto"]),
			semconv.HTTPUserAgent(req.Headers["User-Agent"]),
			semconv.NetHostName(req.Headers["Host"]),
		}...))
}

func convertCustomObjectIntoBytes(
	parentSpan trace.Span,
	customObject *CustomObject,
) (
	[]byte,
	error,
) {
	customObjectAsBytes, err := json.Marshal(customObject)
	if err != nil {
		msg := "Converting custom object into JSON bytes has failed."
		fmt.Println(msg)

		parentSpan.SetAttributes([]attribute.KeyValue{
			semconv.OtelStatusCodeError,
			semconv.OtelStatusDescription("Create Lambda is failed."),
			semconv.ExceptionMessage(msg + ": " + err.Error()),
		}...)

		return nil, err
	}
	return customObjectAsBytes, nil
}

func storeObjectInS3(
	ctx context.Context,
	parentSpan trace.Span,
	jsonBody []byte,
) error {

	fmt.Println("Storing custom object into S3...")

	// Start S3 put span
	ctx, s3PutSpan := startS3PutSpan(ctx, parentSpan)
	defer s3PutSpan.End()

	// Cause error?
	bucketName := strings.Clone(INPUT_S3_BUCKET_NAME)
	if causeError() {
		bucketName = "wrong-bucket-name"
	}

	// Upload object to S3
	_, err := uploader.UploadWithContext(
		ctx,
		&s3manager.UploadInput{
			Bucket: aws.String(bucketName),
			Key:    aws.String(strconv.FormatInt(time.Now().UTC().UnixMilli(), 10)),
			Body:   bytes.NewReader(jsonBody),
		})

	if err != nil {
		msg := "Storing custom object into S3 is failed."

		s3PutSpan.SetAttributes([]attribute.KeyValue{
			semconv.OtelStatusCodeError,
			semconv.OtelStatusDescription("Create Lambda is failed."),
			semconv.ExceptionMessage(msg + ": " + err.Error()),
		}...)

		fmt.Println(msg)
		return err
	}

	fmt.Println("Storing custom object into S3 is succeeded.")
	return nil
}

func causeError() bool {
	return randomizer.Intn(15) == 1
}

func startS3PutSpan(
	ctx context.Context,
	parentSpan trace.Span,
) (
	context.Context,
	trace.Span,
) {
	// Start S3 put span
	return parentSpan.TracerProvider().Tracer(OTEL_SERVICE_NAME).
		Start(ctx, "S3.PutObject",
			trace.WithSpanKind(trace.SpanKindClient),
			trace.WithAttributes([]attribute.KeyValue{
				semconv.NetTransportTCP,
			}...))
}

func enrichSpanWithEvent(
	span trace.Span,
	isSuccesful bool,
) {
	span.AddEvent(CUSTOM_OTEL_SPAN_EVENT_NAME,
		trace.WithAttributes(
			attribute.Bool("is.successful", isSuccesful),
			attribute.String("bucket.id", INPUT_S3_BUCKET_NAME),
		))
}
