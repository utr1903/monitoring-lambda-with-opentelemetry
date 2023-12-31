package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"math/rand"
	"os"
	"time"

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

const (
	OTEL_STATUS_ERROR_DESCRIPTION = "Check Lambda is failed."
	CUSTOM_OTEL_SPAN_EVENT_NAME   = "LambdaCheckEvent"
)

var (
	randomizer        = rand.New(rand.NewSource(time.Now().UnixNano()))
	OTEL_SERVICE_NAME string

	uploader   *s3manager.Uploader
	downloader *s3manager.Downloader
)

type CustomObject struct {
	Item      string `json:"item"`
	IsUpdated bool   `json:"isUpdated"`
	IsChecked bool   `json:"isChecked"`
}

func main() {

	// Parse environment variables
	OTEL_SERVICE_NAME = os.Getenv("OTEL_SERVICE_NAME")

	// Create a s3 downloader & uploader
	sess := session.Must(session.NewSession())
	downloader = s3manager.NewDownloader(sess)
	uploader = s3manager.NewUploader(sess)

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
	sqsEvent events.SQSEvent,
) {

	ctx := context.Background()

	// Loop over all s3 records
	for _, record := range sqsEvent.Records {

		// Start parent span
		ctx, parentSpan := startParentSpan(ctx, record)
		defer parentSpan.End()

		// Parse SQS message
		message, err := parseSqsMessage(parentSpan, record)
		if err != nil {
			enrichSpanWithEvent(parentSpan, false)
			return
		}
		bucketName := (*message)["bucket"]
		keyName := (*message)["key"]

		// Get the object from S3
		customObjectAsBytes, err := getObjectFromS3(ctx, parentSpan, bucketName, keyName)
		if err != nil {
			enrichSpanWithEvent(parentSpan, false)
			return
		}

		// Update custom object
		customObject, err := checkCustomObject(parentSpan, customObjectAsBytes)
		if err != nil {
			enrichSpanWithEvent(parentSpan, false)
			return
		}

		// Convert updated custom object to bytes
		customObjectCheckedAsBytes, err := convertCustomObjectUpdatedIntoBytes(parentSpan, customObject)
		if err != nil {
			enrichSpanWithEvent(parentSpan, false)
			return
		}

		// Store the custom object in output S3
		err = storeCustomObjectInS3(ctx, parentSpan, bucketName, keyName, customObjectCheckedAsBytes)
		if err != nil {
			enrichSpanWithEvent(parentSpan, false)
			return
		}

		enrichSpanWithEvent(parentSpan, true)
	}
}

func startParentSpan(
	ctx context.Context,
	record events.SQSMessage,
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
			semconv.FaaSTriggerPubsub,
			semconv.MessagingOperationProcess,
			semconv.MessagingDestinationKindQueue,
			semconv.MessagingSystem("AmazonSQS"),
			semconv.MessagingMessageID(*aws.String(record.MessageId)),
		}...))
}

func parseSqsMessage(
	parentSpan trace.Span,
	record events.SQSMessage,
) (
	*map[string]string,
	error,
) {
	fmt.Println("Parsing SQS message...")

	message := &map[string]string{}
	err := json.Unmarshal([]byte(record.Body), message)

	if err != nil {
		msg := "Parsing SQS message is failed."

		parentSpan.SetAttributes([]attribute.KeyValue{
			semconv.OtelStatusCodeError,
			semconv.OtelStatusDescription(OTEL_STATUS_ERROR_DESCRIPTION),
		}...)

		parentSpan.RecordError(err, trace.WithAttributes(
			semconv.ExceptionEscaped(true),
		))

		fmt.Println(msg)
		return nil, err
	}

	fmt.Println("Parsing SQS message is succeeded.")
	return message, nil
}

func getObjectFromS3(
	ctx context.Context,
	parentSpan trace.Span,
	bucketName string,
	keyName string,
) (
	[]byte,
	error,
) {

	fmt.Println("Getting custom object from the S3...")

	// Start S3 put span
	ctx, s3GetSpan := startS3GetSpan(ctx, parentSpan)
	defer s3GetSpan.End()

	// Create a writer
	buff := &aws.WriteAtBuffer{}

	// Cause error?
	if causeError() {
		keyName = "wrong-bucket-name"
	}

	// Get object from S3
	_, err := downloader.DownloadWithContext(
		ctx,
		buff,
		&s3.GetObjectInput{
			Bucket: aws.String(bucketName),
			Key:    aws.String(keyName),
		})

	if err != nil {
		msg := "Getting custom object from the S3 is failed."

		s3GetSpan.SetAttributes([]attribute.KeyValue{
			semconv.OtelStatusCodeError,
			semconv.OtelStatusDescription(OTEL_STATUS_ERROR_DESCRIPTION),
		}...)

		s3GetSpan.RecordError(err, trace.WithAttributes(
			semconv.ExceptionEscaped(true),
		))

		fmt.Println(msg)
		return nil, err
	}

	fmt.Println("Getting custom object from the S3 is succeeded.")
	return buff.Bytes(), err
}

func startS3GetSpan(
	ctx context.Context,
	parentSpan trace.Span,
) (
	context.Context,
	trace.Span,
) {
	// Start S3 get span
	return parentSpan.TracerProvider().Tracer(OTEL_SERVICE_NAME).
		Start(ctx, "S3.GetObject",
			trace.WithSpanKind(trace.SpanKindClient),
			trace.WithAttributes([]attribute.KeyValue{
				semconv.NetTransportTCP,
			}...))
}

func checkCustomObject(
	parentSpan trace.Span,
	customObjectAsBytes []byte,
) (
	*CustomObject,
	error,
) {
	customObject := &CustomObject{}
	err := json.Unmarshal(customObjectAsBytes, customObject)
	if err != nil {

		msg := "Parsing custom object is failed."

		parentSpan.SetAttributes([]attribute.KeyValue{
			semconv.OtelStatusCodeError,
			semconv.OtelStatusDescription(OTEL_STATUS_ERROR_DESCRIPTION),
		}...)

		parentSpan.RecordError(err, trace.WithAttributes(
			semconv.ExceptionEscaped(true),
		))

		fmt.Println(msg + ": " + err.Error())
		return nil, err
	}

	customObject.IsChecked = true
	return customObject, nil
}

func convertCustomObjectUpdatedIntoBytes(
	parentSpan trace.Span,
	customObjectUpdated *CustomObject,
) (
	[]byte,
	error,
) {
	customObjectUpdatedAsBytes, err := json.Marshal(customObjectUpdated)
	if err != nil {
		msg := "Converting custom object into JSON bytes has failed."
		fmt.Println(msg)

		parentSpan.SetAttributes([]attribute.KeyValue{
			semconv.OtelStatusCodeError,
			semconv.OtelStatusDescription(OTEL_STATUS_ERROR_DESCRIPTION),
		}...)

		parentSpan.RecordError(err, trace.WithAttributes(
			semconv.ExceptionEscaped(true),
		))

		return nil, err
	}
	return customObjectUpdatedAsBytes, nil
}

func storeCustomObjectInS3(
	ctx context.Context,
	parentSpan trace.Span,
	bucketName string,
	keyName string,
	customObjectUpdatedAsBytes []byte,
) error {

	fmt.Println("Storing custom object into output S3...")

	// Start S3 put span
	ctx, s3PutSpan := startS3PutSpan(ctx, parentSpan)
	defer s3PutSpan.End()

	// Upload object to S3
	_, err := uploader.UploadWithContext(
		ctx,
		&s3manager.UploadInput{
			Bucket: aws.String(bucketName),
			Key:    aws.String(keyName),
			Body:   bytes.NewReader(customObjectUpdatedAsBytes),
		})

	if err != nil {
		msg := "Storing custom object into output S3 is failed."

		s3PutSpan.SetAttributes([]attribute.KeyValue{
			semconv.OtelStatusCodeError,
			semconv.OtelStatusDescription(OTEL_STATUS_ERROR_DESCRIPTION),
		}...)

		s3PutSpan.RecordError(err, trace.WithAttributes(
			semconv.ExceptionEscaped(true),
		))

		fmt.Println(msg)
		return err
	}

	fmt.Println("Storing custom object into output S3 is succeeded.")
	return nil
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

func causeError() bool {
	return randomizer.Intn(15) == 1
}

func enrichSpanWithEvent(
	span trace.Span,
	isSuccesful bool,
) {
	span.AddEvent(CUSTOM_OTEL_SPAN_EVENT_NAME,
		trace.WithAttributes(
			attribute.Bool("is.successful", isSuccesful),
		))
}
