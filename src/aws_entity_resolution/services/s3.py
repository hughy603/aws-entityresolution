"""S3 service for interacting with AWS S3."""

from aws_entity_resolution.config import Settings
from aws_entity_resolution.utils.aws import get_aws_client
from aws_entity_resolution.utils.error import handle_exceptions
from aws_entity_resolution.utils.logging import get_logger, log_event

logger = get_logger(__name__)


class S3Service:
    """S3 service for interacting with AWS S3.

    This service provides methods for interacting with AWS S3, including:
    - Listing objects and prefixes
    - Reading and writing objects
    - Finding the latest file based on prefix patterns

    Examples:
        >>> from aws_entity_resolution.config import get_settings
        >>> from aws_entity_resolution.services.s3 import S3Service
        >>>
        >>> settings = get_settings()
        >>> s3_service = S3Service(settings)
        >>>
        >>> # List objects with a prefix
        >>> result = s3_service.list_objects("data/")
        >>> print(f"Found {len(result['files'])} files")
        >>>
        >>> # Find the latest file with a pattern
        >>> latest = s3_service.find_latest_path(file_pattern=".csv")
        >>> if latest:
        >>>     print(f"Latest file: {latest}")
    """

    def __init__(self: "S3Service", settings: Settings) -> None:
        """Initialize with settings.

        Args:
            settings: Application settings containing AWS region and S3 configuration
        """
        self.settings = settings
        self.client = get_aws_client("s3", region_name=settings.aws_region)

    @handle_exceptions("s3_list_objects")
    def list_objects(self: "S3Service", prefix: str, delimiter: str = "/") -> dict[str, list[str]]:
        """List objects in the S3 bucket with the given prefix.

        Args:
            prefix: The prefix to list objects under
            delimiter: Delimiter character for hierarchical listing (default: "/")

        Returns:
            Dictionary with 'prefixes' and 'files' keys containing lists of prefixes and file keys

        Raises:
            ClientError: If the S3 operation fails
        """
        response = self.client.list_objects_v2(
            Bucket=self.settings.s3.bucket,
            Prefix=prefix,
            Delimiter=delimiter,
        )

        result = {"prefixes": [], "files": []}

        # Extract prefixes (folders)
        if "CommonPrefixes" in response:
            result["prefixes"] = [p["Prefix"] for p in response["CommonPrefixes"]]

        # Extract files
        if "Contents" in response:
            result["files"] = [obj["Key"] for obj in response["Contents"]]

        log_event(
            "s3_list_complete",
            bucket=self.settings.s3.bucket,
            prefix=prefix,
            prefix_count=len(result["prefixes"]),
            file_count=len(result["files"]),
        )

        return result

    @handle_exceptions("s3_write")
    def write_object(self: "S3Service", key: str, data: str) -> None:
        """Write data to an S3 object.

        Args:
            key: S3 object key to write to
            data: String content to write

        Raises:
            ClientError: If the S3 operation fails
        """
        self.client.put_object(
            Bucket=self.settings.s3.bucket,
            Key=key,
            Body=data,
        )

        log_event(
            "s3_write_complete",
            bucket=self.settings.s3.bucket,
            key=key,
            bytes=len(data),
        )

    @handle_exceptions("s3_read")
    def read_object(self: "S3Service", key: str) -> str:
        """Read data from an S3 object.

        Args:
            key: S3 object key to read from

        Returns:
            String content of the S3 object

        Raises:
            ClientError: If the S3 operation fails
        """
        response = self.client.get_object(
            Bucket=self.settings.s3.bucket,
            Key=key,
        )

        data = response["Body"].read().decode("utf-8")

        log_event(
            "s3_read_complete",
            bucket=self.settings.s3.bucket,
            key=key,
            bytes=len(data),
        )

        return data

    @handle_exceptions("s3_find_latest")
    def find_latest_path(
        self: "S3Service",
        base_prefix: str = "",
        file_pattern: str = ".json",
    ) -> str | None:
        """Find the latest file in S3 matching the pattern.

        Args:
            base_prefix: Base prefix to search in (default: "")
            file_pattern: File pattern to match (default: ".json")

        Returns:
            The key of the latest file, or None if no files match

        Raises:
            ClientError: If the S3 operation fails
        """
        result = self.list_objects(base_prefix, delimiter="/")
        prefixes = result.get("prefixes", [])

        if not prefixes:
            # If no prefixes, check for files directly
            files = result.get("files", [])
            matching_files = [f for f in files if file_pattern in f]
            return matching_files[0] if matching_files else None

        # Sort prefixes in descending order (latest first)
        sorted_prefixes = sorted(prefixes, reverse=True)

        # For each prefix (starting with the latest), look for matching files
        for prefix in sorted_prefixes:
            prefix_result = self.list_objects(prefix, delimiter="")
            files = prefix_result.get("files", [])
            matching_files = [f for f in files if file_pattern in f]

            if matching_files:
                # Return the first matching file in the latest directory
                return matching_files[0]

        log_event(
            "s3_find_latest_complete",
            bucket=self.settings.s3.bucket,
            base_prefix=base_prefix,
            file_pattern=file_pattern,
            matching_prefixes=len(sorted_prefixes) if sorted_prefixes else 0,
            latest_prefix=sorted_prefixes[0] if sorted_prefixes else None,
        )

        return None

    @handle_exceptions("s3_get_uri")
    def get_s3_uri(self: "S3Service", key: str) -> str:
        """Get the S3 URI for a key.

        Args:
            key: S3 object key

        Returns:
            S3 URI in the format s3://bucket/key
        """
        return f"s3://{self.settings.s3.bucket}/{key}"
