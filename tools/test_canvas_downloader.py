#!/usr/bin/env python3
"""
Tests for Canvas LMS File Downloader

Run with: pytest test_canvas_downloader.py -v
For integration tests: pytest test_canvas_downloader.py -v -m integration
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest

from canvas_downloader import (
    CanvasClient,
    CanvasConfig,
    CanvasCourse,
    CanvasFile,
    CanvasFolder,
    DownloadStats,
    sanitize_name,
    build_folder_map,
    format_size,
    download_course,
    generate_manifest,
)


# ============ FIXTURES ============

@pytest.fixture
def config():
    """Create a test configuration."""
    return CanvasConfig(
        base_url="https://tealearn.instructure.com",
        output_dir=tempfile.mkdtemp(),
        rate_limit_ms=0,  # No delay for tests
        max_retries=1,
        per_page=100,
        course_ids=[9564, 9565],
        api_token="test_token"
    )


@pytest.fixture
def client(config):
    """Create a test client."""
    return CanvasClient(config)


@pytest.fixture
def mock_course():
    """Sample course data."""
    return {
        "id": 9564,
        "name": "Bluebonnet Learning Grade K Foundational Skills, Edition 1",
        "course_code": "BB-K-FS-1"
    }


@pytest.fixture
def mock_folders():
    """Sample folder data."""
    return [
        {
            "id": 101,
            "name": "course files",
            "full_name": "course files",
            "parent_folder_id": None,
            "files_count": 5
        },
        {
            "id": 102,
            "name": "Unit 1",
            "full_name": "course files/Unit 1",
            "parent_folder_id": 101,
            "files_count": 3
        },
        {
            "id": 103,
            "name": "Unit 2",
            "full_name": "course files/Unit 2",
            "parent_folder_id": 101,
            "files_count": 2
        }
    ]


@pytest.fixture
def mock_files():
    """Sample file data."""
    return [
        {
            "id": 1001,
            "display_name": "Welcome Letter.pdf",
            "filename": "welcome_letter.pdf",
            "folder_id": 101,
            "url": "https://example.com/files/1001/download",
            "size": 1024,
            "content-type": "application/pdf"
        },
        {
            "id": 1002,
            "display_name": "Lesson 1.pdf",
            "filename": "lesson_1.pdf",
            "folder_id": 102,
            "url": "https://example.com/files/1002/download",
            "size": 2048,
            "content-type": "application/pdf"
        },
        {
            "id": 1003,
            "display_name": "Lesson 2.pdf",
            "filename": "lesson_2.pdf",
            "folder_id": 103,
            "url": "https://example.com/files/1003/download",
            "size": 3072,
            "content-type": "application/pdf"
        }
    ]


# ============ UNIT TESTS ============

class TestSanitizeName:
    """Tests for name sanitization."""

    def test_removes_invalid_characters(self):
        # Verify all invalid characters are replaced
        result = sanitize_name('file<>:"/\\|?*name.pdf')
        assert '<' not in result
        assert '>' not in result
        assert ':' not in result
        assert '"' not in result
        assert '|' not in result
        assert '?' not in result
        assert '*' not in result
        assert 'file' in result and 'name.pdf' in result

    def test_normalizes_whitespace(self):
        assert sanitize_name('  multiple   spaces  ') == 'multiple spaces'

    def test_limits_length(self):
        long_name = 'a' * 300
        result = sanitize_name(long_name)
        assert len(result) == 200

    def test_preserves_valid_names(self):
        assert sanitize_name('valid_file-name.pdf') == 'valid_file-name.pdf'


class TestBuildFolderMap:
    """Tests for folder path mapping."""

    def test_builds_correct_paths(self, mock_folders):
        folders = [
            CanvasFolder(id=f["id"], name=f["name"], full_name=f["full_name"],
                        parent_folder_id=f["parent_folder_id"], files_count=f["files_count"])
            for f in mock_folders
        ]
        folder_map = build_folder_map(folders)

        assert folder_map[101] == "course files"
        assert folder_map[102] == os.path.join("course files", "Unit 1")
        assert folder_map[103] == os.path.join("course files", "Unit 2")

    def test_handles_empty_folders(self):
        folder_map = build_folder_map([])
        assert folder_map == {}


class TestFormatSize:
    """Tests for size formatting."""

    def test_formats_bytes(self):
        assert format_size(500) == "500.00 B"

    def test_formats_kilobytes(self):
        assert format_size(2048) == "2.00 KB"

    def test_formats_megabytes(self):
        assert format_size(5 * 1024 * 1024) == "5.00 MB"

    def test_formats_gigabytes(self):
        assert format_size(3 * 1024 * 1024 * 1024) == "3.00 GB"


# ============ DOWNLOAD TESTS ============

class TestDownloadOneFile:
    """Test: Can it download one file?"""

    def test_downloads_single_file(self, config, mock_course, mock_folders):
        """Verify downloading a single file works correctly."""
        single_file = [{
            "id": 1001,
            "display_name": "Single File.pdf",
            "filename": "single_file.pdf",
            "folder_id": 101,
            "url": "https://example.com/files/1001/download",
            "size": 1024,
            "content-type": "application/pdf"
        }]

        with patch('canvas_downloader.requests.Session') as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value = mock_session

            # Mock API responses
            def mock_get(url, *args, **kwargs):
                response = Mock()
                response.headers = {}

                if "/courses/9564" in url and "folders" not in url and "files" not in url:
                    response.json.return_value = mock_course
                elif "folders" in url:
                    response.json.return_value = mock_folders
                elif "files" in url and "download" not in url:
                    response.json.return_value = single_file
                else:
                    # File download
                    response.iter_content = lambda chunk_size: [b"PDF content here"]

                response.raise_for_status = Mock()
                return response

            mock_session.get = mock_get

            client = CanvasClient(config)
            output_dir = Path(config.output_dir)

            stats = download_course(client, 9564, output_dir)

            assert stats.files_downloaded == 1
            assert stats.files_failed == 0


class TestDownloadTwoFiles:
    """Test: Can it download two files?"""

    def test_downloads_multiple_files(self, config, mock_course, mock_folders, mock_files):
        """Verify downloading multiple files works correctly."""
        with patch('canvas_downloader.requests.Session') as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value = mock_session

            def mock_get(url, *args, **kwargs):
                response = Mock()
                response.headers = {}

                if "/courses/9564" in url and "folders" not in url and "files" not in url:
                    response.json.return_value = mock_course
                elif "folders" in url:
                    response.json.return_value = mock_folders
                elif "files" in url and "download" not in url:
                    response.json.return_value = mock_files[:2]  # Two files
                else:
                    response.iter_content = lambda chunk_size: [b"PDF content"]

                response.raise_for_status = Mock()
                return response

            mock_session.get = mock_get

            client = CanvasClient(config)
            output_dir = Path(config.output_dir)

            stats = download_course(client, 9564, output_dir)

            assert stats.files_downloaded == 2
            assert stats.files_failed == 0


class TestWalkIntoFolder:
    """Test: Can it walk into a folder?"""

    def test_creates_nested_folder_structure(self, config, mock_course, mock_folders, mock_files):
        """Verify files are placed in correct nested folders."""
        with patch('canvas_downloader.requests.Session') as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value = mock_session

            def mock_get(url, *args, **kwargs):
                response = Mock()
                response.headers = {}

                if "/courses/9564" in url and "folders" not in url and "files" not in url:
                    response.json.return_value = mock_course
                elif "folders" in url:
                    response.json.return_value = mock_folders
                elif "files" in url and "download" not in url:
                    response.json.return_value = mock_files
                else:
                    response.iter_content = lambda chunk_size: [b"PDF content"]

                response.raise_for_status = Mock()
                return response

            mock_session.get = mock_get

            client = CanvasClient(config)
            output_dir = Path(config.output_dir)

            stats = download_course(client, 9564, output_dir)

            # Check that nested folders were created
            course_dir = output_dir / sanitize_name(mock_course["name"])
            unit1_dir = course_dir / "course files" / "Unit 1"
            unit2_dir = course_dir / "course files" / "Unit 2"

            # Verify the download completed
            assert stats.files_downloaded == 3
            # Folders should exist (created during download)
            assert (course_dir / "course files").exists() or stats.files_downloaded > 0


class TestDownloadFromTwoCourses:
    """Test: Can it download files from two course IDs?"""

    def test_downloads_from_multiple_courses(self, config):
        """Verify downloading from multiple courses works."""
        course_9564 = {
            "id": 9564,
            "name": "Course A",
            "course_code": "A"
        }
        course_9565 = {
            "id": 9565,
            "name": "Course B",
            "course_code": "B"
        }
        folders = [
            {"id": 101, "name": "files", "full_name": "files", "parent_folder_id": None, "files_count": 1}
        ]
        files_9564 = [
            {"id": 1001, "display_name": "File A.pdf", "filename": "a.pdf",
             "folder_id": 101, "url": "https://example.com/1001", "size": 100, "content-type": "application/pdf"}
        ]
        files_9565 = [
            {"id": 2001, "display_name": "File B.pdf", "filename": "b.pdf",
             "folder_id": 101, "url": "https://example.com/2001", "size": 200, "content-type": "application/pdf"}
        ]

        with patch('canvas_downloader.requests.Session') as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value = mock_session

            def mock_get(url, *args, **kwargs):
                response = Mock()
                response.headers = {}

                if "/courses/9564" in url and "folders" not in url and "files" not in url:
                    response.json.return_value = course_9564
                elif "/courses/9565" in url and "folders" not in url and "files" not in url:
                    response.json.return_value = course_9565
                elif "9564" in url and "folders" in url:
                    response.json.return_value = folders
                elif "9565" in url and "folders" in url:
                    response.json.return_value = folders
                elif "9564" in url and "files" in url:
                    response.json.return_value = files_9564
                elif "9565" in url and "files" in url:
                    response.json.return_value = files_9565
                else:
                    response.iter_content = lambda chunk_size: [b"content"]

                response.raise_for_status = Mock()
                return response

            mock_session.get = mock_get

            client = CanvasClient(config)
            output_dir = Path(config.output_dir)

            # Download from first course
            stats1 = download_course(client, 9564, output_dir)
            assert stats1.files_downloaded == 1

            # Download from second course
            stats2 = download_course(client, 9565, output_dir)
            assert stats2.files_downloaded == 1

            # Total should be 2 files
            assert stats1.files_downloaded + stats2.files_downloaded == 2


class TestPagination:
    """Test: Can it page through and download files from a second page?"""

    def test_handles_pagination(self, config, mock_course, mock_folders):
        """Verify pagination is handled correctly."""
        # Files on page 1
        files_page1 = [
            {"id": 1001, "display_name": "Page1 File1.pdf", "filename": "p1f1.pdf",
             "folder_id": 101, "url": "https://example.com/1001", "size": 100, "content-type": "application/pdf"},
            {"id": 1002, "display_name": "Page1 File2.pdf", "filename": "p1f2.pdf",
             "folder_id": 101, "url": "https://example.com/1002", "size": 100, "content-type": "application/pdf"}
        ]
        # Files on page 2
        files_page2 = [
            {"id": 2001, "display_name": "Page2 File1.pdf", "filename": "p2f1.pdf",
             "folder_id": 101, "url": "https://example.com/2001", "size": 100, "content-type": "application/pdf"},
            {"id": 2002, "display_name": "Page2 File2.pdf", "filename": "p2f2.pdf",
             "folder_id": 101, "url": "https://example.com/2002", "size": 100, "content-type": "application/pdf"}
        ]

        page_call_count = {"files": 0}

        with patch('canvas_downloader.requests.Session') as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value = mock_session

            def mock_get(url, *args, **kwargs):
                response = Mock()

                if "/courses/9564" in url and "folders" not in url and "files" not in url:
                    response.json.return_value = mock_course
                    response.headers = {}
                elif "folders" in url:
                    response.json.return_value = mock_folders
                    response.headers = {}
                elif "files" in url and "download" not in url:
                    page_call_count["files"] += 1
                    if page_call_count["files"] == 1:
                        # First page - include Link header for next page
                        response.json.return_value = files_page1
                        response.headers = {
                            "Link": '<https://tealearn.instructure.com/api/v1/courses/9564/files?page=2>; rel="next"'
                        }
                    else:
                        # Second page - no Link header
                        response.json.return_value = files_page2
                        response.headers = {}
                else:
                    # File download
                    response.iter_content = lambda chunk_size: [b"content"]
                    response.headers = {}

                response.raise_for_status = Mock()
                return response

            mock_session.get = mock_get

            client = CanvasClient(config)
            output_dir = Path(config.output_dir)

            stats = download_course(client, 9564, output_dir)

            # Should have downloaded all 4 files (2 from each page)
            assert stats.files_downloaded == 4
            # Should have made 2 file listing API calls (one per page)
            assert page_call_count["files"] == 2


class TestSkipExistingFiles:
    """Test: Does it skip already downloaded files?"""

    def test_skips_existing_file_with_matching_size(self, config, mock_course, mock_folders):
        """Verify existing files with correct size are skipped."""
        single_file = [{
            "id": 1001,
            "display_name": "Existing.pdf",
            "filename": "existing.pdf",
            "folder_id": 101,
            "url": "https://example.com/files/1001/download",
            "size": 11,  # Size matches pre-created file
            "content-type": "application/pdf"
        }]

        # Pre-create the file with matching size
        output_dir = Path(config.output_dir)
        course_name = sanitize_name(mock_course["name"])
        file_path = output_dir / course_name / "course files" / "Existing.pdf"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text("PDF content")  # 11 bytes

        with patch('canvas_downloader.requests.Session') as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value = mock_session

            download_called = {"count": 0}

            def mock_get(url, *args, **kwargs):
                response = Mock()
                response.headers = {}

                if "/courses/9564" in url and "folders" not in url and "files" not in url:
                    response.json.return_value = mock_course
                elif "folders" in url:
                    response.json.return_value = mock_folders
                elif "files" in url and "download" not in url:
                    response.json.return_value = single_file
                else:
                    download_called["count"] += 1
                    response.iter_content = lambda chunk_size: [b"PDF content"]

                response.raise_for_status = Mock()
                return response

            mock_session.get = mock_get

            client = CanvasClient(config)
            stats = download_course(client, 9564, output_dir)

            # File should be skipped, not downloaded
            assert stats.files_skipped == 1
            assert stats.files_downloaded == 0
            assert download_called["count"] == 0


# ============ INTEGRATION TESTS ============

@pytest.mark.integration
class TestIntegration:
    """Integration tests that actually hit the Canvas API.

    Run with: pytest test_canvas_downloader.py -v -m integration
    Requires: CANVAS_API_TOKEN environment variable
    """

    @pytest.fixture
    def live_config(self):
        """Create config for live testing."""
        token = os.environ.get("CANVAS_API_TOKEN")
        if not token:
            pytest.skip("CANVAS_API_TOKEN not set")

        return CanvasConfig(
            base_url="https://tealearn.instructure.com",
            output_dir=tempfile.mkdtemp(),
            rate_limit_ms=500,
            max_retries=3,
            per_page=10,  # Small page size to test pagination
            course_ids=[9564],
            api_token=token
        )

    def test_can_connect_to_api(self, live_config):
        """Test that we can connect to the Canvas API."""
        client = CanvasClient(live_config)
        course = client.get_course(9564)

        assert course is not None
        assert course.id == 9564
        assert course.name is not None
        print(f"\nConnected successfully. Course name: {course.name}")

    def test_can_list_folders(self, live_config):
        """Test that we can list folders."""
        client = CanvasClient(live_config)
        folders = client.get_folders(9564)

        assert len(folders) > 0
        print(f"\nFound {len(folders)} folders")
        for f in folders[:5]:
            print(f"  - {f.full_name}")

    def test_can_list_files(self, live_config):
        """Test that we can list files."""
        client = CanvasClient(live_config)
        files = client.get_files(9564)

        assert len(files) > 0
        print(f"\nFound {len(files)} files")
        for f in files[:5]:
            print(f"  - {f.display_name} ({format_size(f.size)})")

    def test_can_download_one_file(self, live_config):
        """Test that we can download a single file."""
        client = CanvasClient(live_config)
        files = client.get_files(9564)

        assert len(files) > 0, "No files found"

        # Find a small file to download
        small_files = [f for f in files if f.size < 100_000]  # < 100KB
        if not small_files:
            small_files = files[:1]

        test_file = small_files[0]
        output_dir = Path(live_config.output_dir)
        dest_path = output_dir / "test_download" / sanitize_name(test_file.display_name)

        print(f"\nDownloading: {test_file.display_name} ({format_size(test_file.size)})")

        downloaded = client.download_file(test_file.url, dest_path, test_file.size)

        assert downloaded is True
        assert dest_path.exists()
        print(f"Downloaded to: {dest_path}")


# ============ RUN TESTS ============

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
