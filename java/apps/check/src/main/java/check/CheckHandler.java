package check;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.DataOutputStream;
import java.io.InputStream;
import java.io.PrintWriter;
import java.io.StringWriter;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;
import java.util.Random;

import com.amazonaws.services.lambda.runtime.Context;
import com.amazonaws.services.lambda.runtime.LambdaLogger;
import com.amazonaws.services.lambda.runtime.RequestHandler;
import com.amazonaws.services.lambda.runtime.events.SQSEvent;
import com.amazonaws.services.lambda.runtime.events.SQSEvent.SQSMessage;
import com.google.gson.Gson;

import check.daos.CustomObject;
import io.opentelemetry.api.common.AttributeKey;
import io.opentelemetry.api.common.Attributes;
import io.opentelemetry.api.trace.Span;
import io.opentelemetry.semconv.trace.attributes.SemanticAttributes;
import software.amazon.awssdk.core.ResponseBytes;
import software.amazon.awssdk.core.SdkSystemSetting;
import software.amazon.awssdk.core.sync.RequestBody;
import software.amazon.awssdk.http.ContentStreamProvider;
import software.amazon.awssdk.http.urlconnection.UrlConnectionHttpClient;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.model.GetObjectRequest;
import software.amazon.awssdk.services.s3.model.GetObjectResponse;
import software.amazon.awssdk.services.s3.model.PutObjectRequest;

public class CheckHandler implements RequestHandler<SQSEvent, Void> {

  static {
    // https://docs.aws.amazon.com/de_de/sdk-for-java/latest/developer-guide/security-java-tls.html
    System.setProperty("jdk.tls.client.protocols", "TLSv1.2");
  }

  private LambdaLogger logger;

  private static final String CUSTOM_OTEL_SPAN_EVENT_NAME = "LambdaCheckEvent";

  private Gson gson = new Gson();
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

  @Override
  public Void handleRequest(
      SQSEvent input,
      Context context) {

    logger = context.getLogger();

    // Check if there are any records
    if (input.getRecords().isEmpty()) {
      logger.log("No records are found in S3 event.");
      return null;
    }

    // Parse SQS message
    Map<String, String> message = parseSqsMessage(input);
    String bucketName = message.get("bucket");
    String keyName = message.get("key");

    try {

      // Create the custom object from input bucket
      String customObjectAsString = getCustomObjectFromS3(bucketName, keyName);

      // Update custom object
      String customObjectCheckedAsString = checkCustomObject(customObjectAsString);

      // Store the custom object in S3
      storeCustomObjectInS3(bucketName, keyName, customObjectCheckedAsString);

      // Enrich span with success
      enrichSpanWithSuccess(context, bucketName, keyName);

      logger.log("Checking custom object is succeeded.");
      return null;
    } catch (Exception e) {
      logger.log("Checking custom object is failed!: " + e);

      // Enrich span with failure
      enrichSpanWithFailure(context, e, bucketName, keyName);

      return null;
    }
  }

  @SuppressWarnings("unchecked")
  private Map<String, String> parseSqsMessage(
      SQSEvent input) {

    logger.log("Parsing SQS message...");

    // Get bucket name and object key
    SQSMessage record = input.getRecords().get(0);
    String messageAsString = record.getBody();

    // Parse message
    Map<String, String> message = new HashMap<String, String>();
    message = gson.fromJson(messageAsString, message.getClass());

    logger.log("Parsing SQS message is succeeded.");
    return message;
  }

  private String getCustomObjectFromS3(
      String bucketName,
      String keyName) throws Exception {

    logger.log("Getting custom object from the S3...");

    // Cause error?
    if (causeError())
      keyName = "wrong-key-name";

    try {
      GetObjectRequest getObjectRequest = GetObjectRequest
          .builder()
          .bucket(bucketName)
          .key(keyName)
          .build();

      // Get custom object as bytes
      ResponseBytes<GetObjectResponse> responseBytes = s3Client.getObjectAsBytes(getObjectRequest);
      byte[] customObjectAsBytes = responseBytes.asByteArray();

      logger.log("Getting custom object from the S3 is succedeed.");

      // Parse as string and return
      return new String(customObjectAsBytes, StandardCharsets.UTF_8);
    } catch (Exception e) {
      String msg = "Getting custom object from the S3 is failed.";
      logger.log(msg);
      throw new Exception(msg + ": " + e.getMessage());
    }
  }

  private String checkCustomObject(
      String customObjectAsString) {
    CustomObject customObject = gson.fromJson(customObjectAsString, CustomObject.class);
    customObject.setIsChecked(true);

    return gson.toJson(customObject);
  }

  private void storeCustomObjectInS3(
      String bucketName,
      String keyName,
      String customObjectString) {

    logger.log("Checking custom object...");

    // Get byte array stream of string
    ByteArrayOutputStream jsonByteStream = getByteArrayOutputStream(customObjectString);

    // Prepare an InputStream from the ByteArrayOutputStream
    InputStream fis = new ByteArrayInputStream(jsonByteStream.toByteArray());

    // Put file into S3
    s3Client.putObject(
        PutObjectRequest
            .builder()
            .bucket(bucketName)
            .key(keyName)
            .build(),
        RequestBody.fromContentProvider(new ContentStreamProvider() {
          @Override
          public InputStream newStream() {
            return fis;
          }
        }, jsonByteStream.toByteArray().length, "application/json"));

    logger.log("Checking custom object is succedeed.");
  }

  private ByteArrayOutputStream getByteArrayOutputStream(
      String data) throws RuntimeException {

    // Convert string to byte array
    ByteArrayOutputStream byteArrayOutputStream = new ByteArrayOutputStream();
    DataOutputStream out = new DataOutputStream(byteArrayOutputStream);
    try {
      out.write(data.getBytes());
      byteArrayOutputStream.flush();
      byteArrayOutputStream.close();
    } catch (Exception e) {
      throw new RuntimeException("getByteArrayOutputStream failed", e);
    }
    return byteArrayOutputStream;
  }

  private boolean causeError() {
    // Cause an error if the random number is 1
    int n = random.nextInt(15);
    return n == 1;
  }

  private void enrichSpanWithSuccess(
      Context context,
      String bucketName,
      String keyName) {

    Span span = Span.current();

    Attributes eventAttributes = Attributes.of(
        AttributeKey.booleanKey("is.successful"), true,
        AttributeKey.stringKey("bucket.id"), bucketName,
        AttributeKey.stringKey("key.name"), keyName,
        AttributeKey.stringKey("aws.request.id"), context.getAwsRequestId());

    span.addEvent(CUSTOM_OTEL_SPAN_EVENT_NAME, eventAttributes);
  }

  private void enrichSpanWithFailure(
      Context context,
      Exception e,
      String bucketName,
      String keyName) {

    Span span = Span.current();
    span.setAttribute(SemanticAttributes.OTEL_STATUS_CODE, SemanticAttributes.OtelStatusCodeValues.ERROR);
    span.setAttribute(SemanticAttributes.OTEL_STATUS_DESCRIPTION, "Check Lambda is failed.");
    span.setAttribute(SemanticAttributes.EXCEPTION_TYPE, e.getClass().getCanonicalName());
    span.setAttribute(SemanticAttributes.EXCEPTION_MESSAGE, e.getMessage());
    span.setAttribute(SemanticAttributes.EXCEPTION_STACKTRACE, convertExceptionStackTraceToString(e));

    Attributes eventAttributes = Attributes.of(
        AttributeKey.booleanKey("is.successful"), false,
        AttributeKey.stringKey("bucket.id"), bucketName,
        AttributeKey.stringKey("key.name"), keyName,
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
