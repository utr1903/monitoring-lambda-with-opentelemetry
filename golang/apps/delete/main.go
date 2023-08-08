package main

import (
	"context"
	"fmt"
	"math/rand"
	"os"
	"time"

	"github.com/aws/aws-lambda-go/lambda"
	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/s3"
	"github.com/aws/aws-sdk-go/service/s3/s3iface"
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
	OTEL_STATUS_ERROR_DESCRIPTION = "Delete Lambda is failed."
	CUSTOM_OTEL_SPAN_EVENT_NAME   = "LambdaDeleteEvent"
)

var (
	randomizer           = rand.New(rand.NewSource(time.Now().UnixNano()))
	OTEL_SERVICE_NAME    string
	INPUT_S3_BUCKET_NAME string

	s3Api          s3iface.S3API
	deleteIterator s3manager.BatchDeleteIterator
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

	// Create a s3 iterator
	sess := session.Must(session.NewSession())
	s3Api = s3.New(sess)
	deleteIterator = s3manager.NewDeleteListIterator(
		s3Api,
		&s3.ListObjectsInput{
			Bucket: aws.String(INPUT_S3_BUCKET_NAME),
		})

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

func handler() {

	ctx := context.Background()

	// Start parent span
	ctx, parentSpan := startParentSpan(ctx)
	defer parentSpan.End()

	// Delete all custom objects in S3
	err := deleteAllCustomObjectsInS3(ctx, parentSpan)
	if err != nil {
		enrichSpanWithEvent(parentSpan, false)
		return
	}

	enrichSpanWithEvent(parentSpan, true)
}

func startParentSpan(
	ctx context.Context,
) (
	context.Context,
	trace.Span,
) {
	// Create tracer
	tracer := otel.Tracer(OTEL_SERVICE_NAME)

	// Start parent span
	return tracer.Start(ctx, "main.handler",
		trace.WithSpanKind(trace.SpanKindServer),
		trace.WithAttributes([]attribute.KeyValue{
			semconv.FaaSTriggerTimer,
		}...))
}

func deleteAllCustomObjectsInS3(
	ctx context.Context,
	parentSpan trace.Span,
) error {

	fmt.Println("Deleting all custom object in S3...")

	// Start S3 put span
	ctx, s3DeleteSpan := startS3DeleteSpan(ctx, parentSpan)
	defer s3DeleteSpan.End()

	var err error
	if causeError() {
		deleteIteratorLocal := s3manager.NewDeleteListIterator(
			s3Api,
			&s3.ListObjectsInput{
				Bucket: aws.String("wrong-bucket-name"),
			})
		err = s3manager.NewBatchDeleteWithClient(s3Api).
			Delete(ctx, deleteIteratorLocal)
	} else {

		err = s3manager.NewBatchDeleteWithClient(s3Api).
			Delete(ctx, deleteIterator)
	}

	if err != nil {
		msg := "Deleting all custom object in S3 is failed."

		s3DeleteSpan.SetAttributes([]attribute.KeyValue{
			semconv.OtelStatusCodeError,
			semconv.OtelStatusDescription(OTEL_STATUS_ERROR_DESCRIPTION),
			semconv.ExceptionMessage(msg + ": " + err.Error()),
		}...)

		fmt.Println(msg)
		return err
	}

	fmt.Println("Deleting all custom object in S3 is succeeded.")
	return nil
}

func startS3DeleteSpan(
	ctx context.Context,
	parentSpan trace.Span,
) (
	context.Context,
	trace.Span,
) {
	// Start S3 put span
	return parentSpan.TracerProvider().Tracer(OTEL_SERVICE_NAME).
		Start(ctx, "S3.DeleteObjects",
			trace.WithSpanKind(trace.SpanKindClient),
			trace.WithAttributes([]attribute.KeyValue{
				semconv.NetTransportTCP,
			}...))
}

func causeError() bool {
	return randomizer.Intn(3) == 1
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
