package create;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.DataOutputStream;
import java.io.InputStream;
import java.io.PrintWriter;
import java.io.StringWriter;
import java.util.HashMap;
import java.util.Map;
import java.util.Random;

import com.amazonaws.services.lambda.runtime.Context;
import com.amazonaws.services.lambda.runtime.LambdaLogger;
import com.amazonaws.services.lambda.runtime.RequestHandler;
import com.amazonaws.services.lambda.runtime.events.APIGatewayProxyRequestEvent;
import com.amazonaws.services.lambda.runtime.events.APIGatewayProxyResponseEvent;
import com.google.gson.Gson;

import create.daos.CustomObject;
import io.opentelemetry.api.common.AttributeKey;
import io.opentelemetry.api.common.Attributes;
import io.opentelemetry.api.trace.Span;
import io.opentelemetry.semconv.trace.attributes.SemanticAttributes;
import software.amazon.awssdk.core.SdkSystemSetting;
import software.amazon.awssdk.core.sync.RequestBody;
import software.amazon.awssdk.http.ContentStreamProvider;
import software.amazon.awssdk.http.urlconnection.UrlConnectionHttpClient;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.model.PutObjectRequest;

public class CreateHandler implements RequestHandler<APIGatewayProxyRequestEvent, APIGatewayProxyResponseEvent> {

  static {
    // https://docs.aws.amazon.com/de_de/sdk-for-java/latest/developer-guide/security-java-tls.html
    System.setProperty("jdk.tls.client.protocols", "TLSv1.2");
  }

  private LambdaLogger logger;

  private static String INPUT_S3_BUCKET_NAME;
  private static final String CUSTOM_OTEL_SPAN_EVENT_NAME = "LambdaCreateEvent";

  private final static S3Client s3Client;
  private Gson gson = new Gson();
  private Random random = new Random(System.currentTimeMillis());

  static {
    final String region = System.getenv(SdkSystemSetting.AWS_REGION.environmentVariable());
    final Region awsRegion = region != null ? Region.of(region) : Region.EU_WEST_1;
    s3Client = S3Client.builder()
        .httpClient(UrlConnectionHttpClient.builder().build())
        .region(awsRegion)
        .build();
  }

  @Override
  public APIGatewayProxyResponseEvent handleRequest(
      APIGatewayProxyRequestEvent input,
      Context context) {

    logger = context.getLogger();

    try {
      // Parse environment variables
      parseEnvVars();

      // Create the custom object
      CustomObject customObject = createCustomObject();

      // Stringify custom object
      String json = getStringOfCustomObject(customObject);

      // Store the custom object in S3
      storeObjectInS3(json);

      // Enrich span with success
      enrichSpanWithSuccess(context);

      return createResponse(200, json);
    } catch (Exception e) {
      logger.log("Storing custom object into S3 is failed! Exception: " + e);

      // Enrich span with success
      enrichSpanWithFailure(context, e);

      return createResponse(500, e.getMessage());
    }
  }

  private void parseEnvVars() {
    logger.log("Parsing environment variables...");
    INPUT_S3_BUCKET_NAME = System.getenv("INPUT_S3_BUCKET_NAME");
    logger.log("Parsing environment variables is succeeded.");
  }

  private CustomObject createCustomObject() {
    return new CustomObject(
        "test",
        false,
        false);
  }

  private String getStringOfCustomObject(
      CustomObject customObject) {
    // Convert object to string
    return gson.toJson(customObject);
  }

  private void storeObjectInS3(
      String customObjectString) throws Exception {

    logger.log("Storing custom object into S3...");

    // Get byte array stream of string
    ByteArrayOutputStream jsonByteStream = getByteArrayOutputStream(customObjectString);

    // Prepare an InputStream from the ByteArrayOutputStream
    InputStream fis = new ByteArrayInputStream(jsonByteStream.toByteArray());

    // Cause error?
    String bucketName = String.valueOf(INPUT_S3_BUCKET_NAME);
    if (causeError())
      bucketName = "wrong-bucket-name";

    // Put file into S3
    try {
      s3Client.putObject(
          PutObjectRequest
              .builder()
              .bucket(bucketName)
              .key(String.valueOf(System.currentTimeMillis()))
              .build(),
          RequestBody.fromContentProvider(new ContentStreamProvider() {
            @Override
            public InputStream newStream() {
              return fis;
            }
          }, jsonByteStream.toByteArray().length, "application/json"));

      logger.log("Storing custom object into S3 is succeeded.");
    } catch (Exception e) {
      String msg = "Storing custom object into S3 is failed";
      logger.log(msg);
      throw new Exception(msg + ": " + e.getMessage());
    }
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

  private APIGatewayProxyResponseEvent createResponse(
      int statusCode,
      String body) {
    Map<String, String> responseHeaders = new HashMap<>();
    responseHeaders.put("Content-Type", "application/json");
    APIGatewayProxyResponseEvent response = new APIGatewayProxyResponseEvent().withHeaders(responseHeaders);

    return response
        .withStatusCode(statusCode)
        .withBody(body);
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
    span.setAttribute(SemanticAttributes.OTEL_STATUS_DESCRIPTION, "Create Lambda is failed.");
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
