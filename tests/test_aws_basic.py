def test_s3_operations(s3_client):
    """Test that S3 mocking is working properly."""
    # Create a test bucket
    bucket_name = "test-bucket"
    s3_client.create_bucket(
        Bucket=bucket_name, CreateBucketConfiguration={"LocationConstraint": "us-west-2"}
    )

    # Check bucket exists
    response = s3_client.list_buckets()
    buckets = [bucket["Name"] for bucket in response["Buckets"]]
    assert bucket_name in buckets

    # Put an object
    s3_client.put_object(Bucket=bucket_name, Key="test-key", Body="test-content")

    # Check object exists
    response = s3_client.list_objects_v2(Bucket=bucket_name)
    assert "Contents" in response
    assert response["Contents"][0]["Key"] == "test-key"
