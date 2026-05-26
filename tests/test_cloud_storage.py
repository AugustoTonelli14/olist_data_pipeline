"""Unit tests for the cloud storage module."""

from unittest.mock import MagicMock, patch

import pytest

from storage.cloud_storage import (
    ensure_bucket,
    get_s3_client,
    upload_directory,
    upload_file,
)


class TestGetS3Client:
    """Tests for S3 client factory."""

    def test_local_returns_client(self):
        """Local provider should return a boto3 client."""
        with patch("storage.cloud_storage.CLOUD_PROVIDER", "local"):
            client = get_s3_client()
            assert client is not None

    def test_invalid_provider_raises(self):
        """Invalid provider should raise ValueError."""
        with patch("storage.cloud_storage.CLOUD_PROVIDER", "invalid"):
            with pytest.raises(ValueError, match="Invalid CLOUD_PROVIDER"):
                get_s3_client()


class TestEnsureBucket:
    """Tests for bucket creation."""

    def test_creates_bucket_when_missing(self):
        """Should call create_bucket when head_bucket raises."""
        from botocore.exceptions import ClientError

        mock_client = MagicMock()
        mock_client.head_bucket.side_effect = ClientError(
            {"Error": {"Code": "404"}}, "HeadBucket"
        )
        ensure_bucket(mock_client, "test-bucket")
        mock_client.create_bucket.assert_called_once_with(
            Bucket="test-bucket"
        )

    def test_skips_creation_when_exists(self):
        """Should not call create_bucket when bucket exists."""
        mock_client = MagicMock()
        mock_client.head_bucket.return_value = {}
        ensure_bucket(mock_client, "test-bucket")
        mock_client.create_bucket.assert_not_called()


class TestUploadFile:
    """Tests for single file upload."""

    def test_upload_calls_boto(self, tmp_path):
        """Should call upload_file on the client."""
        test_file = tmp_path / "test.csv"
        test_file.write_text("a,b\n1,2")
        mock_client = MagicMock()

        upload_file(mock_client, test_file, "bucket", "test.csv")
        mock_client.upload_file.assert_called_once_with(
            str(test_file), "bucket", "test.csv"
        )


class TestUploadDirectory:
    """Tests for directory upload."""

    def test_uploads_matching_files(self, tmp_path):
        """Should upload only files matching the pattern."""
        (tmp_path / "a.csv").write_text("data")
        (tmp_path / "b.csv").write_text("data")
        (tmp_path / "c.txt").write_text("data")
        (tmp_path / ".gitkeep").write_text("")

        mock_client = MagicMock()
        mock_client.head_bucket.return_value = {}

        count = upload_directory(mock_client, tmp_path, "bucket", "*.csv")
        assert count == 2

    def test_returns_zero_when_no_files(self, tmp_path):
        """Should return 0 when no files match."""
        mock_client = MagicMock()
        count = upload_directory(mock_client, tmp_path, "bucket", "*.parquet")
        assert count == 0
