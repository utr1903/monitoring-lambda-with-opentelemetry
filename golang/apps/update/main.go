package main

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"strconv"

	"github.com/aws/aws-lambda-go/events"
	"github.com/aws/aws-lambda-go/lambda"
	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/s3"
	"github.com/aws/aws-sdk-go/service/s3/s3manager"
	"go.opentelemetry.io/contrib/instrumentation/github.com/aws/aws-lambda-go/otellambda"
	"go.opentelemetry.io/contrib/instrumentation/github.com/aws/aws-lambda-go/otellambda/xrayconfig"
	"go.opentelemetry.io/contrib/propagators/aws/xray"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	semconv "go.opentelemetry.io/otel/semconv/v1.17.0"
	"go.opentelemetry.io/otel/trace"
)

var (
	OTEL_SERVICE_NAME     string
	OUTPUT_S3_BUCKET_NAME string
	SQS_QUEUE_URL         string
	downloader            *s3manager.Downloader
)

type CustomObject struct {
	Item      string `json:"item"`
	IsUpdated bool   `json:"isUpdated"`
	IsChecked bool   `json:"isChecked"`
}

func main() {

	// Parse environment variables
	OTEL_SERVICE_NAME = os.Getenv("OTEL_SERVICE_NAME")
	OUTPUT_S3_BUCKET_NAME = os.Getenv("INPUT_S3_BUCKET_NAME")
	SQS_QUEUE_URL = os.Getenv("SQS_QUEUE_URL")

	// Create a s3 downloader
	downloader = s3manager.NewDownloader(session.Must(session.NewSession()))

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
	ctx context.Context,
	s3Event events.S3Event,
) {

	// Loop over all s3 records
	for _, record := range s3Event.Records {

		s3 := record.S3
		fmt.Printf("[%s - %s] Bucket = %s, Key = %s \n", record.EventSource, record.EventTime, s3.Bucket.Name, s3.Object.Key)

		// Start parent span
		ctx, parentSpan := startParentSpan(ctx, record)
		defer parentSpan.End()

		// Get the object from input S3
		objectBytes, err := getObjectFromS3(ctx, parentSpan, record)
		if err != nil {
			return
		}

		customObject := &CustomObject{}
		json.Unmarshal(objectBytes, customObject)

		fmt.Println("Item: " + customObject.Item)
		fmt.Println("IsUpdated: " + strconv.FormatBool(customObject.IsUpdated))
		fmt.Println("IsChecked: " + strconv.FormatBool(customObject.IsChecked))
	}
}

func startParentSpan(
	ctx context.Context,
	record events.S3EventRecord,
) (
	context.Context,
	trace.Span,
) {
	// Create tracer
	tracer := otel.Tracer(OTEL_SERVICE_NAME)

	// Start parent span
	return tracer.Start(ctx, "main.handler",
		trace.WithSpanKind(trace.SpanKindConsumer),
		trace.WithAttributes([]attribute.KeyValue{
			semconv.FaaSTriggerDatasource,
			semconv.FaaSDocumentOperationInsert,
			semconv.FaaSDocumentTime(record.EventTime.UTC().String()),
			semconv.FaaSDocumentCollection(record.S3.Bucket.Name),
			semconv.FaaSDocumentName(record.S3.Object.Key),
		}...))
}

func getObjectFromS3(
	ctx context.Context,
	parentSpan trace.Span,
	record events.S3EventRecord,
) (
	[]byte,
	error,
) {

	// Start S3 put span
	ctx, s3GetSpan := startS3GetSpan(ctx, parentSpan)
	defer s3GetSpan.End()

	// Create a writer
	buff := &aws.WriteAtBuffer{}

	// Get object from input S3
	_, err := downloader.DownloadWithContext(
		ctx,
		buff,
		&s3.GetObjectInput{
			Bucket: aws.String(record.S3.Bucket.Name),
			Key:    aws.String(record.S3.Object.Key),
		})

	if err != nil {
		s3GetSpan.SetAttributes([]attribute.KeyValue{
			semconv.OtelStatusCodeError,
		}...)
		return nil, err
	}

	return buff.Bytes(), err
}

func startS3GetSpan(
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
