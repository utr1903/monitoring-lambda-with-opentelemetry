package delete;

import java.io.PrintWriter;
import java.io.StringWriter;
import java.util.ArrayList;
import java.util.List;
import java.util.Random;

import com.amazonaws.services.lambda.runtime.Context;
import com.amazonaws.services.lambda.runtime.LambdaLogger;

import io.opentelemetry.api.common.AttributeKey;
import io.opentelemetry.api.common.Attributes;
import io.opentelemetry.api.trace.Span;
import io.opentelemetry.semconv.trace.attributes.SemanticAttributes;
import software.amazon.awssdk.core.SdkSystemSetting;
import software.amazon.awssdk.http.urlconnection.UrlConnectionHttpClient;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.model.Delete;
import software.amazon.awssdk.services.s3.model.DeleteObjectsRequest;
import software.amazon.awssdk.services.s3.model.DeleteObjectsResponse;
import software.amazon.awssdk.services.s3.model.ListObjectsV2Request;
import software.amazon.awssdk.services.s3.model.ListObjectsV2Response;
import software.amazon.awssdk.services.s3.model.ObjectIdentifier;
import software.amazon.awssdk.services.s3.model.S3Error;
import software.amazon.awssdk.services.s3.model.S3Object;

public class DeleteHandler {

  static {
    // https://docs.aws.amazon.com/de_de/sdk-for-java/latest/developer-guide/security-java-tls.html
    System.setProperty("jdk.tls.client.protocols", "TLSv1.2");
  }

  private LambdaLogger logger;

  private static String INPUT_S3_BUCKET_NAME;
  private static final String CUSTOM_OTEL_SPAN_EVENT_NAME = "LambdaDeleteEvent";

  private Random random = new Random(System.currentTimeMillis());

  private final static S3Client s3Client;

  static {
    final String region = System.getenv(SdkSystemSetting.AWS_REGION.environmentVariable());
    final Region awsRegion = region != null ? Region.of(region) : Region.EU_WEST_1;

    s3Client = S3Client.builder()
        .httpClient(UrlConnectionHttpClient.builder().build())
        .region(awsRegion)
        .build();
  }

  public Void handleRequest(
      Context context) {

    logger = context.getLogger();

    try {
      // Parse environment variables
      parseEnvVars();

      // Get all custom objects in input bucket
      List<S3Object> allCustomObjects = getAllCustomObjectsInInputS3();

      // Delete the custom objects in input bucket
      deleteAllCustomObjectsInInputS3(allCustomObjects);

      // Enrich span with success
      enrichSpanWithSuccess(context);

      return null;
    } catch (Exception e) {
      logger.log("Deleting custom objects in the input S3 is failed!: " + e);

      // Enrich span with failure
      enrichSpanWithFailure(context, e);

      return null;
    }
  }

  private void parseEnvVars() {
    logger.log("Parsing env vars...");
    INPUT_S3_BUCKET_NAME = System.getenv("INPUT_S3_BUCKET_NAME");
    logger.log("Parsing env vars is succeeded.");
  }

  private List<S3Object> getAllCustomObjectsInInputS3() throws Exception {

    logger.log("Getting all custom objects in the input S3...");

    String bucketName = String.valueOf(INPUT_S3_BUCKET_NAME);
    if (causeError())
      bucketName = "wrong-bucket-name";

    try {
      // List all objects in the bucket
      ListObjectsV2Request listRequest = ListObjectsV2Request.builder()
          .bucket(bucketName)
          .build();

      List<S3Object> allCustomObjects = new ArrayList<>();
      ListObjectsV2Response listResponse;

      do {
        listResponse = s3Client.listObjectsV2(listRequest);
        allCustomObjects.addAll(listResponse.contents());

        listRequest = ListObjectsV2Request.builder()
            .bucket(bucketName)
            .continuationToken(listResponse.nextContinuationToken())
            .build();

      } while (listResponse.isTruncated());

      logger.log("Getting all custom objects in the input S3 is succeeded.");
      return allCustomObjects;
    } catch (Exception e) {
      String msg = "Getting all custom objects in the input S3 is failed";
      logger.log(msg);
      throw new Exception(msg + ": " + e.getMessage());
    }
  }

  private void deleteAllCustomObjectsInInputS3(
      List<S3Object> allCustomObjects) {

    logger.log("Deleting all custom objects in the input S3...");

    // Delete the objects
    List<ObjectIdentifier> objectIdentifiersForDeletion = new ArrayList<>();

    for (S3Object object : allCustomObjects)
      objectIdentifiersForDeletion.add(ObjectIdentifier.builder().key(object.key()).build());

    DeleteObjectsRequest deleteRequest = DeleteObjectsRequest.builder()
        .bucket(INPUT_S3_BUCKET_NAME)
        .delete(Delete.builder().objects(objectIdentifiersForDeletion).build())
        .build();

    DeleteObjectsResponse deleteObjects = s3Client.deleteObjects(deleteRequest);

    if (deleteObjects.hasErrors()) {
      logger.log("Deleting all custom objects in the input S3 is failed!");

      List<S3Error> errors = deleteObjects.errors();
      for (S3Error error : errors)
        logger.log("S3 Error: " + error);

      return;
    }

    logger.log("Deleting custom objects in the input S3 is succeeded.");
  }

  private boolean causeError() {
    // Cause an error if the random number is 1
    int n = random.nextInt(3);
    return n == 1;
  }

  private void enrichSpanWithSuccess(
      Context context) {

    Span span = Span.current();

    Attributes eventAttributes = Attributes.of(
        AttributeKey.booleanKey("is.successful"), true,
        AttributeKey.stringKey("bucket.id"), INPUT_S3_BUCKET_NAME,
        AttributeKey.stringKey("aws.request.id"), context.getAwsRequestId());

    span.addEvent(CUSTOM_OTEL_SPAN_EVENT_NAME, eventAttributes);
  }

  private void enrichSpanWithFailure(
      Context context,
      Exception e) {

    Span span = Span.current();
    span.setAttribute(SemanticAttributes.OTEL_STATUS_CODE, SemanticAttributes.OtelStatusCodeValues.ERROR);
    span.setAttribute(SemanticAttributes.OTEL_STATUS_DESCRIPTION, "Delete Lambda is failed.");
    span.setAttribute(SemanticAttributes.EXCEPTION_TYPE, e.getClass().getCanonicalName());
    span.setAttribute(SemanticAttributes.EXCEPTION_MESSAGE, e.getMessage());
    span.setAttribute(SemanticAttributes.EXCEPTION_STACKTRACE, convertExceptionStackTraceToString(e));

    Attributes eventAttributes = Attributes.of(
        AttributeKey.booleanKey("is.successful"), false,
        AttributeKey.stringKey("bucket.id"), INPUT_S3_BUCKET_NAME,
        AttributeKey.stringKey("aws.request.id"), context.getAwsRequestId());

    span.addEvent(CUSTOM_OTEL_SPAN_EVENT_NAME, eventAttributes);
  }

  private String convertExceptionStackTraceToString(
      Exception e) {
    StringWriter sw = new StringWriter();
    PrintWriter pw = new PrintWriter(sw);
    e.printStackTrace(pw);
    return sw.toString();
  }
}
