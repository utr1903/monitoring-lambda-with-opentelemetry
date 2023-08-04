package delete;

import java.util.ArrayList;
import java.util.List;

import com.amazonaws.services.lambda.runtime.Context;
import com.amazonaws.services.lambda.runtime.LambdaLogger;

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

      return null;
    } catch (Exception e) {
      logger.log("Deleting custom objects in the input S3 is failed!: " + e);
      return null;
    }
  }

  private void parseEnvVars() {
    logger.log("Parsing env vars...");
    INPUT_S3_BUCKET_NAME = System.getenv("INPUT_S3_BUCKET_NAME");
    logger.log("Parsing env vars is succeeded.");
  }

  private List<S3Object> getAllCustomObjectsInInputS3() {

    logger.log("Getting all custom objects in the input S3...");

    // List all objects in the bucket
    ListObjectsV2Request listRequest = ListObjectsV2Request.builder()
        .bucket(INPUT_S3_BUCKET_NAME)
        .build();

    List<S3Object> allCustomObjects = new ArrayList<>();
    ListObjectsV2Response listResponse;

    do {
      listResponse = s3Client.listObjectsV2(listRequest);
      allCustomObjects.addAll(listResponse.contents());

      listRequest = ListObjectsV2Request.builder()
          .bucket(INPUT_S3_BUCKET_NAME)
          .continuationToken(listResponse.nextContinuationToken())
          .build();

    } while (listResponse.isTruncated());

    logger.log("Getting all custom objects in the input S3 is succeeded.");

    return allCustomObjects;
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
}
