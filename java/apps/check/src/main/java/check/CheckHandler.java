package check;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.DataOutputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;

import com.amazonaws.services.lambda.runtime.Context;
import com.amazonaws.services.lambda.runtime.LambdaLogger;
import com.amazonaws.services.lambda.runtime.RequestHandler;
import com.amazonaws.services.lambda.runtime.events.SQSEvent;
import com.amazonaws.services.lambda.runtime.events.SQSEvent.SQSMessage;
import com.google.gson.Gson;

import check.daos.CustomObject;
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

  private static String OUTPUT_S3_BUCKET_NAME;

  private Gson gson = new Gson();

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

    try {
      // Parse environment variables
      parseEnvVars();

      // Check if there are any records
      if (input.getRecords().isEmpty()) {
        logger.log("No records are found in S3 event.");
        return null;
      }

      // Parse SQS message
      Map<String, String> message = parseSqsMessage(input);

      // Create the custom object from input bucket
      String customObjectAsString = getCustomObjectFromInputS3(
          message.get("bucket"),
          message.get("key"));

      // Update custom object
      String customObjectUpdatedAsString = updateCustomObject(customObjectAsString);

      // Store the custom object in S3
      storeCustomObjectInOutputS3(message.get("key"), customObjectUpdatedAsString);

      logger.log("Updating custom object is succeeded.");
      return null;
    } catch (Exception e) {
      logger.log("Updating custom object is failed!: " + e);
      return null;
    }
  }

  private void parseEnvVars() {
    logger.log("Parsing env vars...");
    OUTPUT_S3_BUCKET_NAME = System.getenv("OUTPUT_S3_BUCKET_NAME");
    logger.log("Parsing env vars is succeeded.");
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

  private String getCustomObjectFromInputS3(
      String bucket,
      String key) {

    logger.log("Getting custom object S3 info from the SQS message...");

    GetObjectRequest getObjectRequest = null;
    getObjectRequest = GetObjectRequest
        .builder()
        .bucket(bucket)
        .key(key)
        .build();

    logger.log("Getting custom object S3 info from the SQS message is succeeded.");
    // Get custom object as bytes
    ResponseBytes<GetObjectResponse> responseBytes = s3Client.getObjectAsBytes(getObjectRequest);
    byte[] customObjectAsBytes = responseBytes.asByteArray();

    logger.log("Getting custom object is succedeed.");

    // Parse as string and return
    return new String(customObjectAsBytes, StandardCharsets.UTF_8);
  }

  private String updateCustomObject(
      String customObjectAsString) {
    CustomObject customObject = gson.fromJson(customObjectAsString, CustomObject.class);
    customObject.setIsChecked(true);

    return gson.toJson(customObject);
  }

  private void storeCustomObjectInOutputS3(
      String key,
      String customObjectString) {

    logger.log("Updating custom object...");

    // Get byte array stream of string
    ByteArrayOutputStream jsonByteStream = getByteArrayOutputStream(customObjectString);

    // Prepare an InputStream from the ByteArrayOutputStream
    InputStream fis = new ByteArrayInputStream(jsonByteStream.toByteArray());

    // Put file into S3
    s3Client.putObject(
        PutObjectRequest
            .builder()
            .bucket(OUTPUT_S3_BUCKET_NAME)
            .key(key)
            .build(),
        RequestBody.fromContentProvider(new ContentStreamProvider() {
          @Override
          public InputStream newStream() {
            return fis;
          }
        }, jsonByteStream.toByteArray().length, "application/json"));

    logger.log("Updating custom object is succedeed.");
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
}
