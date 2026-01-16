#!/usr/bin/env python3
"""
Canvas LMS File Downloader

A reusable tool for downloading all files from Canvas LMS courses.
Supports authentication via API token, session cookie, or browser cookies.

FAIL-FAST POLICY: This tool stops immediately on errors. No silent failures.

Usage:
    python canvas_downloader.py --manifest-only  # Catalog only
    python canvas_downloader.py                   # Full download
    python canvas_downloader.py --course 9564     # Single course
    python canvas_downloader.py --browser chrome  # Use Chrome cookies
    python canvas_downloader.py --log download.log  # Log to file
"""

import argparse
import json
import logging
import os
import random
import re
import shutil
import sqlite3
import sys
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, NoReturn
from urllib.parse import urlparse

import requests

# ============ LOGGING SETUP ============

class ColorFormatter(logging.Formatter):
    """Colored output for terminal."""

    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[41m',  # Red background
    }
    RESET = '\033[0m'

    def format(self, record):
        color = self.COLORS.get(record.levelname, '')
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logging(log_file: Optional[Path] = None, verbose: bool = False) -> logging.Logger:
    """Configure logging to stdout and optionally to file."""
    logger = logging.getLogger('canvas_downloader')
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger.handlers.clear()

    # Console handler with colors
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.DEBUG if verbose else logging.INFO)
    console_fmt = ColorFormatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S')
    console.setFormatter(console_fmt)
    logger.addHandler(console)

    # File handler (no colors)
    if log_file:
        file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_fmt = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        file_handler.setFormatter(file_fmt)
        logger.addHandler(file_handler)
        logger.info(f"Logging to file: {log_file}")

    return logger


# Global logger
log = logging.getLogger('canvas_downloader')


# ============ FATAL ERROR HANDLING ============

class DownloadFatalError(Exception):
    """Unrecoverable error - stop everything."""
    pass


def fatal(message: str) -> NoReturn:
    """Log fatal error and exit immediately."""
    log.critical("")
    log.critical("=" * 60)
    log.critical("FATAL ERROR - STOPPING IMMEDIATELY")
    log.critical("=" * 60)
    log.critical(message)
    log.critical("=" * 60)
    log.critical("")
    sys.exit(1)


def assert_ok(condition: bool, message: str):
    """Assert condition or die."""
    if not condition:
        fatal(message)


# ============ BACKOFF STRATEGY ============

class BackoffStrategy:
    """Exponential backoff with jitter for responsible API usage."""

    def __init__(self, base_delay: float = 1.0, max_delay: float = 60.0, max_retries: int = 5):
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.max_retries = max_retries
        self.consecutive_errors = 0
        self.total_requests = 0
        self.total_wait_time = 0.0

    def wait_between_requests(self):
        """Standard delay between requests (be a good citizen)."""
        delay = self.base_delay + random.uniform(0, 0.5)
        self.total_wait_time += delay
        time.sleep(delay)

    def wait_after_error(self, attempt: int) -> float:
        """Exponential backoff after an error."""
        # Exponential: 2^attempt * base, with jitter
        delay = min(self.max_delay, (2 ** attempt) * self.base_delay)
        jitter = random.uniform(0, delay * 0.5)
        total_delay = delay + jitter

        log.warning(f"Backing off for {total_delay:.1f}s (attempt {attempt}/{self.max_retries})")
        self.total_wait_time += total_delay
        time.sleep(total_delay)
        return total_delay

    def record_success(self):
        """Reset error counter on success."""
        self.consecutive_errors = 0
        self.total_requests += 1

    def record_error(self):
        """Track consecutive errors."""
        self.consecutive_errors += 1
        self.total_requests += 1

        if self.consecutive_errors >= self.max_retries:
            fatal(f"Too many consecutive errors ({self.consecutive_errors}). Giving up.")

    def get_stats(self) -> dict:
        """Return statistics."""
        return {
            "total_requests": self.total_requests,
            "total_wait_time_seconds": round(self.total_wait_time, 1),
            "consecutive_errors": self.consecutive_errors,
        }


# ============ PROGRESS TRACKING ============

@dataclass
class DownloadProgress:
    """Track download progress with detailed stats."""
    total_courses: int = 0
    completed_courses: int = 0
    total_files: int = 0
    downloaded_files: int = 0
    skipped_files: int = 0
    failed_files: int = 0
    total_bytes: int = 0
    downloaded_bytes: int = 0
    start_time: float = field(default_factory=time.time)
    errors: list = field(default_factory=list)

    def add_error(self, error: str):
        """Record an error."""
        self.errors.append(error)
        log.error(f"ERROR: {error}")

    def log_progress(self):
        """Log current progress."""
        elapsed = time.time() - self.start_time

        if self.total_files > 0:
            pct = (self.downloaded_files + self.skipped_files) / self.total_files * 100
        else:
            pct = 0

        if self.downloaded_bytes > 0 and elapsed > 0:
            rate = self.downloaded_bytes / elapsed / 1024 / 1024  # MB/s
            rate_str = f"{rate:.2f} MB/s"
        else:
            rate_str = "-- MB/s"

        log.info(
            f"Progress: {self.downloaded_files}/{self.total_files} files "
            f"({pct:.1f}%) | {format_size(self.downloaded_bytes)} | {rate_str} | "
            f"Elapsed: {format_duration(elapsed)}"
        )

    def log_summary(self):
        """Log final summary."""
        elapsed = time.time() - self.start_time

        log.info("")
        log.info("=" * 60)
        log.info("DOWNLOAD SUMMARY")
        log.info("=" * 60)
        log.info(f"  Courses:    {self.completed_courses}/{self.total_courses}")
        log.info(f"  Downloaded: {self.downloaded_files} files ({format_size(self.downloaded_bytes)})")
        log.info(f"  Skipped:    {self.skipped_files} files (already existed)")
        log.info(f"  Failed:     {self.failed_files} files")
        log.info(f"  Duration:   {format_duration(elapsed)}")

        if self.errors:
            log.warning("")
            log.warning(f"ERRORS ({len(self.errors)}):")
            for err in self.errors:
                log.warning(f"  - {err}")

        log.info("=" * 60)


# ============ UTILITY FUNCTIONS ============

def format_size(size_bytes: int) -> str:
    """Format byte size as human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} TB"


def format_duration(seconds: float) -> str:
    """Format duration as human-readable string."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        return f"{seconds/60:.0f}m {seconds%60:.0f}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def sanitize_name(name: str, max_length: int = 50) -> str:
    """Sanitize a name for filesystem use.

    Windows has a 260 char path limit. Very aggressive truncation.
    Course (50) + folder (50) + file (50) + base path (~80) = ~230 chars
    """
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', name)
    sanitized = re.sub(r'\s+', ' ', sanitized).strip()
    # Remove trailing underscores/spaces after truncation
    result = sanitized[:max_length].rstrip('_ ')
    return result if result else "unnamed"


def get_safe_path(base_dir: Path, *parts: str) -> Path:
    """Build a path that's safe for Windows (under 260 chars)."""
    # Resolve base to absolute
    base = base_dir.resolve()

    # Build path with sanitized parts - handle parts that contain path separators
    for part in parts:
        # Split on both Windows and Unix separators
        subparts = re.split(r'[/\\]', part)
        for subpart in subparts:
            if subpart:  # Skip empty parts
                base = base / sanitize_name(subpart)

    # Final check - if still too long, truncate more
    path_str = str(base)
    if len(path_str) > 250:
        log.warning(f"Path too long ({len(path_str)} chars), truncating...")
        # Truncate the filename more aggressively
        filename = base.name
        parent = base.parent
        max_filename = 250 - len(str(parent)) - 1
        if max_filename < 10:
            max_filename = 10
        base = parent / sanitize_name(filename, max_filename)

    return base


# ============ COOKIE EXTRACTION ============

# Optional: browser_cookie3 for easier cookie extraction
try:
    import browser_cookie3
    HAS_BROWSER_COOKIE3 = True
except ImportError:
    HAS_BROWSER_COOKIE3 = False


def get_browser_cookies_path(browser: str) -> Optional[Path]:
    """Get the path to browser's cookies database."""
    if sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        app_data = os.environ.get("APPDATA", "")

        paths = {
            "chrome": [
                Path(local_app_data) / "Google/Chrome/User Data/Default/Network/Cookies",
                Path(local_app_data) / "Google/Chrome/User Data/Default/Cookies",
            ],
            "edge": [
                Path(local_app_data) / "Microsoft/Edge/User Data/Default/Network/Cookies",
                Path(local_app_data) / "Microsoft/Edge/User Data/Default/Cookies",
            ],
            "firefox": [Path(app_data) / "Mozilla/Firefox/Profiles"],
        }
    elif sys.platform == "darwin":
        paths = {
            "chrome": [Path.home() / "Library/Application Support/Google/Chrome/Default/Cookies"],
            "edge": [Path.home() / "Library/Application Support/Microsoft Edge/Default/Cookies"],
            "firefox": [Path.home() / "Library/Application Support/Firefox/Profiles"],
        }
    else:
        paths = {
            "chrome": [
                Path.home() / ".config/google-chrome/Default/Cookies",
                Path.home() / ".config/chromium/Default/Cookies",
            ],
            "edge": [Path.home() / ".config/microsoft-edge/Default/Cookies"],
            "firefox": [Path.home() / ".mozilla/firefox"],
        }

    for path in paths.get(browser, []):
        if browser == "firefox" and path.exists():
            for profile_dir in path.iterdir():
                if profile_dir.is_dir():
                    cookies_file = profile_dir / "cookies.sqlite"
                    if cookies_file.exists():
                        return cookies_file
        elif path.exists():
            return path
    return None


def extract_cookies_from_browser(browser: str, domain: str) -> dict[str, str]:
    """Extract cookies from browser for a specific domain."""
    if HAS_BROWSER_COOKIE3:
        try:
            if browser == "chrome":
                cj = browser_cookie3.chrome(domain_name=domain)
            elif browser == "edge":
                cj = browser_cookie3.edge(domain_name=domain)
            elif browser == "firefox":
                cj = browser_cookie3.firefox(domain_name=domain)
            else:
                fatal(f"Unknown browser: {browser}")

            cookies = {c.name: c.value for c in cj if domain in c.domain}
            return cookies
        except Exception as e:
            log.warning(f"browser_cookie3 failed: {e}")
            log.warning("Falling back to manual extraction...")

    db_path = get_browser_cookies_path(browser)
    if not db_path:
        return {}

    log.info(f"Found cookies at: {db_path}")

    temp_db = Path(tempfile.mkdtemp()) / "cookies_copy.db"
    try:
        shutil.copy2(db_path, temp_db)
    except Exception as e:
        log.error(f"Could not copy cookies database: {e}")
        return {}

    cookies = {}
    try:
        conn = sqlite3.connect(str(temp_db))
        cursor = conn.cursor()

        if browser == "firefox":
            cursor.execute("SELECT name, value FROM moz_cookies WHERE host LIKE ?", (f"%{domain}%",))
            for name, value in cursor.fetchall():
                cookies[name] = value
        else:
            cursor.execute("SELECT name, encrypted_value, value FROM cookies WHERE host_key LIKE ?", (f"%{domain}%",))
            for name, encrypted_value, value in cursor.fetchall():
                if value:
                    cookies[name] = value

        conn.close()
    except Exception as e:
        log.error(f"Error reading cookies database: {e}")
    finally:
        try:
            temp_db.unlink()
            temp_db.parent.rmdir()
        except:
            pass

    return cookies


def load_cookies_from_file(cookie_file: Path) -> dict[str, str]:
    """Load cookies from file."""
    assert_ok(cookie_file.exists(), f"Cookie file not found: {cookie_file}")

    content = cookie_file.read_text(encoding="utf-8")
    cookies = {}

    if content.strip().startswith("{"):
        try:
            cookies = json.loads(content)
            log.info(f"Loaded {len(cookies)} cookies from JSON file")
            return cookies
        except json.JSONDecodeError:
            pass

    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        parts = line.split("\t")
        if len(parts) >= 7:
            cookies[parts[5]] = parts[6]
        elif "=" in line:
            name, _, value = line.partition("=")
            cookies[name.strip()] = value.strip()

    log.info(f"Loaded {len(cookies)} cookies from file")
    return cookies


def cookies_to_header(cookies: dict[str, str]) -> str:
    """Convert cookies dict to Cookie header string."""
    return "; ".join(f"{name}={value}" for name, value in cookies.items())


def print_cookie_instructions():
    """Print instructions for manually obtaining cookies."""
    print("""
To get cookies manually:

1. Open your browser and log in to Canvas
2. Open Developer Tools (F12)
3. Go to Network tab
4. Refresh the page
5. Click any request to the Canvas domain
6. Find "Cookie:" in Request Headers
7. Copy the entire cookie string
8. Save to cookies.txt (format: name=value, one per line)

Then run: python canvas_downloader.py --cookie-file cookies.txt
""")


# ============ CONFIGURATION ============

DEFAULT_CONFIG = {
    "base_url": "https://tealearn.instructure.com",
    "output_dir": "../sources/bluebonnet",
    "base_delay_ms": 500,
    "max_retries": 5,
    "per_page": 100,
    "course_ids": [
        9564, 9565, 9534, 9575, 9548, 9549, 9554, 9555, 9532, 9556,
        9533, 9539, 9540, 9541, 9542, 9543, 9535, 9544, 9545, 9546
    ]
}


@dataclass
class CanvasConfig:
    """Configuration for Canvas downloader."""
    base_url: str
    output_dir: str
    base_delay_ms: int
    max_retries: int
    per_page: int
    course_ids: list
    api_token: Optional[str] = None
    session_cookie: Optional[str] = None


# ============ DATA CLASSES ============

@dataclass
class CanvasFile:
    id: int
    display_name: str
    filename: str
    folder_id: int
    url: str
    size: int
    content_type: str


@dataclass
class CanvasFolder:
    id: int
    name: str
    full_name: str
    parent_folder_id: Optional[int]
    files_count: int


@dataclass
class CanvasCourse:
    id: int
    name: str
    course_code: str = ""


# ============ CANVAS API CLIENT ============

class CanvasClient:
    """Client for interacting with Canvas LMS API."""

    def __init__(self, config: CanvasConfig):
        self.config = config
        self.session = requests.Session()
        self.backoff = BackoffStrategy(
            base_delay=config.base_delay_ms / 1000,
            max_retries=config.max_retries
        )
        self._setup_auth()

    def _setup_auth(self):
        """Configure authentication headers."""
        if self.config.api_token:
            self.session.headers["Authorization"] = f"Bearer {self.config.api_token}"
            log.info("Using API token authentication")
        elif self.config.session_cookie:
            self.session.headers["Cookie"] = self.config.session_cookie
            log.info("Using cookie authentication")
        else:
            log.warning("No authentication configured!")

        self.session.headers["Accept"] = "application/json"
        self.session.headers["User-Agent"] = "CanvasDownloader/1.0 (Educational Use)"

    def _request(self, url: str, stream: bool = False) -> requests.Response:
        """Make a request with retry and backoff."""
        last_error = None

        for attempt in range(1, self.config.max_retries + 1):
            try:
                self.backoff.wait_between_requests()

                log.debug(f"GET {url}")
                response = self.session.get(url, stream=stream, timeout=60)

                # Check for rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    log.warning(f"Rate limited! Waiting {retry_after}s...")
                    time.sleep(retry_after)
                    self.backoff.record_error()
                    continue

                # Check for server errors (retry)
                if response.status_code >= 500:
                    log.warning(f"Server error {response.status_code}, retrying...")
                    self.backoff.wait_after_error(attempt)
                    self.backoff.record_error()
                    continue

                # Check for client errors (fail fast)
                if response.status_code >= 400:
                    error_body = response.text[:500]
                    fatal(
                        f"API request failed!\n"
                        f"  URL: {url}\n"
                        f"  Status: {response.status_code}\n"
                        f"  Response: {error_body}"
                    )

                self.backoff.record_success()
                return response

            except requests.exceptions.Timeout as e:
                log.warning(f"Request timeout (attempt {attempt}): {e}")
                self.backoff.wait_after_error(attempt)
                self.backoff.record_error()
                last_error = e

            except requests.exceptions.ConnectionError as e:
                log.warning(f"Connection error (attempt {attempt}): {e}")
                self.backoff.wait_after_error(attempt)
                self.backoff.record_error()
                last_error = e

            except Exception as e:
                fatal(f"Unexpected error during request: {e}")

        fatal(f"Request failed after {self.config.max_retries} attempts: {last_error}")

    def _fetch_all_pages(self, url: str) -> list:
        """Fetch all pages of a paginated endpoint."""
        all_data = []
        separator = "&" if "?" in url else "?"
        current_url = f"{url}{separator}per_page={self.config.per_page}"
        page = 1

        while current_url:
            log.debug(f"Fetching page {page}...")
            response = self._request(current_url)
            data = response.json()

            if isinstance(data, list):
                all_data.extend(data)
                log.debug(f"  Got {len(data)} items (total: {len(all_data)})")
            else:
                return [data] if data else []

            current_url = None
            link_header = response.headers.get("Link", "")
            if link_header:
                for link in link_header.split(","):
                    if 'rel="next"' in link:
                        match = re.search(r'<([^>]+)>', link)
                        if match:
                            current_url = match.group(1)
                            page += 1
                            break

        return all_data

    def get_course(self, course_id: int) -> CanvasCourse:
        """Get course information."""
        log.info(f"Fetching course {course_id}...")
        url = f"{self.config.base_url}/api/v1/courses/{course_id}"
        response = self._request(url)
        data = response.json()

        course = CanvasCourse(
            id=data.get("id", course_id),
            name=data.get("name", f"Course {course_id}"),
            course_code=data.get("course_code", "")
        )
        log.info(f"  Course: {course.name}")
        return course

    def get_folders(self, course_id: int) -> list[CanvasFolder]:
        """Get all folders in a course."""
        log.info(f"Fetching folders for course {course_id}...")
        url = f"{self.config.base_url}/api/v1/courses/{course_id}/folders"
        data = self._fetch_all_pages(url)

        folders = [
            CanvasFolder(
                id=f.get("id"),
                name=f.get("name", ""),
                full_name=f.get("full_name", ""),
                parent_folder_id=f.get("parent_folder_id"),
                files_count=f.get("files_count", 0)
            )
            for f in data
        ]
        log.info(f"  Found {len(folders)} folders")
        return folders

    def get_files(self, course_id: int) -> list[CanvasFile]:
        """Get all files in a course."""
        log.info(f"Fetching files for course {course_id}...")
        url = f"{self.config.base_url}/api/v1/courses/{course_id}/files"
        data = self._fetch_all_pages(url)

        files = [
            CanvasFile(
                id=f.get("id"),
                display_name=f.get("display_name", ""),
                filename=f.get("filename", ""),
                folder_id=f.get("folder_id", 0),
                url=f.get("url", ""),
                size=f.get("size", 0),
                content_type=f.get("content-type", "")
            )
            for f in data
        ]

        total_size = sum(f.size for f in files)
        log.info(f"  Found {len(files)} files ({format_size(total_size)})")
        return files

    def download_file(self, file: CanvasFile, dest_path: Path, progress: DownloadProgress) -> bool:
        """Download a file to the specified path. Returns True if downloaded, False if skipped."""
        # Skip if file exists with correct size
        if dest_path.exists():
            existing_size = dest_path.stat().st_size
            if existing_size == file.size:
                log.debug(f"  SKIP (exists): {file.display_name}")
                return False
            else:
                log.info(f"  Re-downloading (size mismatch): {file.display_name}")

        assert_ok(file.url, f"No download URL for file: {file.display_name}")

        # Create parent directories (handle Windows long paths)
        try:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            log.error(f"  Failed to create directory: {dest_path.parent}")
            log.error(f"  Error: {e}")
            fatal(f"Cannot create directory for {file.display_name}: {e}")

        # Download with streaming
        log.info(f"  Downloading: {file.display_name} ({format_size(file.size)})")

        try:
            response = self._request(file.url, stream=True)

            downloaded = 0
            with open(dest_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

            # Verify download
            actual_size = dest_path.stat().st_size
            if file.size > 0 and actual_size != file.size:
                fatal(
                    f"Download size mismatch!\n"
                    f"  File: {file.display_name}\n"
                    f"  Expected: {file.size} bytes\n"
                    f"  Got: {actual_size} bytes"
                )

            log.info(f"    OK: {format_size(actual_size)}")
            return True

        except Exception as e:
            # Clean up partial file
            if dest_path.exists():
                dest_path.unlink()
            fatal(f"Download failed for {file.display_name}: {e}")


# ============ MAIN OPERATIONS ============

def build_folder_map(folders: list[CanvasFolder]) -> dict[int, str]:
    """Build a mapping of folder IDs to paths."""
    folder_paths = {}
    sorted_folders = sorted(folders, key=lambda f: f.full_name.count('/'))

    for folder in sorted_folders:
        parts = folder.full_name.split('/')
        clean_parts = [sanitize_name(part) for part in parts if part]
        folder_paths[folder.id] = os.path.join(*clean_parts) if clean_parts else ""

    return folder_paths


def generate_manifest(client: CanvasClient, output_dir: Path) -> dict:
    """Generate a manifest of all courses, folders, and files."""
    log.info("")
    log.info("=" * 60)
    log.info("GENERATING MANIFEST")
    log.info("=" * 60)

    manifest = {
        "generated": datetime.utcnow().isoformat() + "Z",
        "base_url": client.config.base_url,
        "courses": []
    }

    for i, course_id in enumerate(client.config.course_ids, 1):
        log.info(f"\n[{i}/{len(client.config.course_ids)}] Course {course_id}")

        course = client.get_course(course_id)
        folders = client.get_folders(course_id)
        files = client.get_files(course_id)

        total_size = sum(f.size for f in files)

        manifest["courses"].append({
            "id": course_id,
            "name": course.name,
            "course_code": course.course_code,
            "folders": [{"id": f.id, "name": f.name, "full_path": f.full_name} for f in folders],
            "files": [{"id": f.id, "name": f.display_name, "folder_id": f.folder_id, "size": f.size} for f in files],
            "total_files": len(files),
            "total_size": total_size
        })

    # Save manifest
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    # Summary
    total_files = sum(c["total_files"] for c in manifest["courses"])
    total_size = sum(c["total_size"] for c in manifest["courses"])

    log.info("")
    log.info("=" * 60)
    log.info("MANIFEST COMPLETE")
    log.info(f"  Courses: {len(manifest['courses'])}")
    log.info(f"  Files: {total_files}")
    log.info(f"  Total Size: {format_size(total_size)}")
    log.info(f"  Saved: {manifest_path}")
    log.info("=" * 60)

    return manifest


def download_course(client: CanvasClient, course_id: int, output_dir: Path, progress: DownloadProgress):
    """Download all files from a single course."""
    log.info("")
    log.info("=" * 60)
    log.info(f"DOWNLOADING COURSE {course_id}")
    log.info("=" * 60)

    course = client.get_course(course_id)
    course_name = sanitize_name(course.name)

    folders = client.get_folders(course_id)
    folder_map = build_folder_map(folders)

    files = client.get_files(course_id)
    progress.total_files += len(files)
    progress.total_bytes += sum(f.size for f in files)

    for i, file in enumerate(files, 1):
        log.info(f"\n[{i}/{len(files)}] {file.display_name}")

        folder_path = folder_map.get(file.folder_id, "unknown_folder")
        file_name = sanitize_name(file.display_name)

        # Build safe path that stays under Windows 260 char limit
        dest_path = get_safe_path(output_dir, course_name, folder_path, file_name)

        downloaded = client.download_file(file, dest_path, progress)

        if downloaded:
            progress.downloaded_files += 1
            progress.downloaded_bytes += file.size
        else:
            progress.skipped_files += 1

        # Log progress every 10 files
        if i % 10 == 0:
            progress.log_progress()

    progress.completed_courses += 1
    log.info(f"\nCourse {course_id} complete!")


def download_all(client: CanvasClient, output_dir: Path):
    """Download all files from all configured courses."""
    log.info("")
    log.info("=" * 60)
    log.info("CANVAS LMS FILE DOWNLOADER")
    log.info("=" * 60)
    log.info(f"Base URL: {client.config.base_url}")
    log.info(f"Output: {output_dir.absolute()}")
    log.info(f"Courses: {len(client.config.course_ids)}")
    log.info(f"Rate limit: {client.config.base_delay_ms}ms between requests")
    log.info("=" * 60)

    output_dir.mkdir(parents=True, exist_ok=True)

    progress = DownloadProgress(total_courses=len(client.config.course_ids))

    for i, course_id in enumerate(client.config.course_ids, 1):
        log.info(f"\n>>> COURSE {i}/{len(client.config.course_ids)}: {course_id}")
        download_course(client, course_id, output_dir, progress)
        progress.log_progress()

    progress.log_summary()

    # Log backoff stats
    stats = client.backoff.get_stats()
    log.info(f"API Stats: {stats['total_requests']} requests, {stats['total_wait_time_seconds']}s total delay")


# ============ CLI ============

def main():
    parser = argparse.ArgumentParser(
        description="Download files from Canvas LMS courses (FAIL-FAST MODE)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python canvas_downloader.py --manifest-only
    python canvas_downloader.py --token YOUR_TOKEN
    python canvas_downloader.py --token YOUR_TOKEN --course 9564
    python canvas_downloader.py --token YOUR_TOKEN --log download.log
    python canvas_downloader.py --browser chrome
    python canvas_downloader.py --cookie-file cookies.txt
    python canvas_downloader.py --cookie-help
"""
    )

    parser.add_argument("--manifest-only", action="store_true", help="Generate manifest without downloading")
    parser.add_argument("--course", type=int, help="Download only this course ID")
    parser.add_argument("--token", type=str, help="Canvas API token")
    parser.add_argument("--cookie", type=str, help="Session cookie string")
    parser.add_argument("--cookie-file", type=str, help="Path to cookie file")
    parser.add_argument("--browser", choices=["chrome", "edge", "firefox"], help="Extract cookies from browser")
    parser.add_argument("--cookie-help", action="store_true", help="Show cookie instructions")
    parser.add_argument("--output", type=str, default=DEFAULT_CONFIG["output_dir"], help="Output directory")
    parser.add_argument("--base-url", type=str, default=DEFAULT_CONFIG["base_url"], help="Canvas LMS URL")
    parser.add_argument("--rate-limit", type=int, default=DEFAULT_CONFIG["base_delay_ms"], help="Delay between requests (ms)")
    parser.add_argument("--log", type=str, help="Log file path")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--test", action="store_true", help="Test connectivity only")

    args = parser.parse_args()

    # Setup logging first
    log_file = Path(args.log) if args.log else None
    setup_logging(log_file, args.verbose)

    if args.cookie_help:
        print_cookie_instructions()
        return

    # Determine authentication
    session_cookie = None
    api_token = args.token or os.environ.get("CANVAS_API_TOKEN")

    if not api_token:
        if args.cookie:
            session_cookie = args.cookie
        elif args.cookie_file:
            cookies = load_cookies_from_file(Path(args.cookie_file))
            assert_ok(bool(cookies), "No cookies loaded from file")
            session_cookie = cookies_to_header(cookies)
        elif args.browser:
            log.info(f"Extracting cookies from {args.browser}...")
            domain = urlparse(args.base_url).netloc
            cookies = extract_cookies_from_browser(args.browser, domain)
            assert_ok(bool(cookies), f"No cookies found for {domain} in {args.browser}")
            session_cookie = cookies_to_header(cookies)
        elif os.environ.get("CANVAS_COOKIE"):
            session_cookie = os.environ.get("CANVAS_COOKIE")

    # Build configuration
    course_ids = [args.course] if args.course else DEFAULT_CONFIG["course_ids"]

    config = CanvasConfig(
        base_url=args.base_url,
        output_dir=args.output,
        base_delay_ms=args.rate_limit,
        max_retries=DEFAULT_CONFIG["max_retries"],
        per_page=DEFAULT_CONFIG["per_page"],
        course_ids=course_ids,
        api_token=api_token,
        session_cookie=session_cookie
    )

    if not config.api_token and not config.session_cookie:
        log.warning("WARNING: No authentication provided!")
        log.warning("Use --token, --browser, --cookie-file, or --cookie")

    client = CanvasClient(config)
    output_dir = Path(config.output_dir)

    # Test mode
    if args.test:
        log.info("Testing API connectivity...")
        course = client.get_course(course_ids[0])
        folders = client.get_folders(course_ids[0])
        files = client.get_files(course_ids[0])

        log.info("")
        log.info("CONNECTION SUCCESSFUL!")
        log.info(f"  Course: {course.name}")
        log.info(f"  Folders: {len(folders)}")
        log.info(f"  Files: {len(files)}")

        if files:
            log.info("  Sample files:")
            for f in files[:5]:
                log.info(f"    - {f.display_name} ({format_size(f.size)})")
        return

    # Execute
    if args.manifest_only:
        generate_manifest(client, output_dir)
    else:
        download_all(client, output_dir)


if __name__ == "__main__":
    main()
