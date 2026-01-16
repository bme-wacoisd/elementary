#!/usr/bin/env python3
"""
Google API Authentication Module for FEA

Handles OAuth2 authentication for Google APIs (Classroom, Docs, Drive).
Uses credentials.json for initial auth and stores tokens in token.json.

Usage:
    from google_auth import get_credentials, get_service

    # Get credentials for multiple scopes
    creds = get_credentials(['classroom', 'docs', 'drive'])

    # Get a specific service
    classroom = get_service('classroom')
    docs = get_service('docs')
"""

import json
import logging
import sys
from pathlib import Path
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)

# Scope definitions
SCOPES = {
    'classroom': [
        'https://www.googleapis.com/auth/classroom.courses',
        'https://www.googleapis.com/auth/classroom.coursework.students',
        'https://www.googleapis.com/auth/classroom.rosters',
    ],
    'docs': [
        'https://www.googleapis.com/auth/documents',
    ],
    'drive': [
        'https://www.googleapis.com/auth/drive.file',
    ],
}

# Service versions
SERVICE_VERSIONS = {
    'classroom': ('classroom', 'v1'),
    'docs': ('docs', 'v1'),
    'drive': ('drive', 'v3'),
}

# Path configuration - credentials in project root
PROJECT_ROOT = Path(__file__).parent.parent
CREDENTIALS_FILE = PROJECT_ROOT / 'credentials.json'
TOKEN_FILE = PROJECT_ROOT / 'token.json'


def get_all_scopes(scope_names: list[str]) -> list[str]:
    """
    Get all OAuth scopes for the requested services.

    Args:
        scope_names: List of service names ('classroom', 'docs', 'drive')

    Returns:
        List of OAuth scope URLs
    """
    all_scopes = []
    for name in scope_names:
        if name not in SCOPES:
            raise ValueError(f"Unknown scope: {name}. Available: {list(SCOPES.keys())}")
        all_scopes.extend(SCOPES[name])
    return list(set(all_scopes))  # Remove duplicates


def get_credentials(scope_names: Optional[list[str]] = None):
    """
    Get Google API credentials, prompting for OAuth if needed.

    Args:
        scope_names: List of service names to request scopes for.
                    Defaults to all available services.

    Returns:
        google.oauth2.credentials.Credentials object

    Raises:
        FileNotFoundError: If credentials.json is missing
        RuntimeError: If authentication fails
    """
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError as e:
        logging.critical(f"Missing required package: {e}")
        logging.critical("Install with: pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client")
        sys.exit(1)

    if scope_names is None:
        scope_names = list(SCOPES.keys())

    scopes = get_all_scopes(scope_names)
    creds = None

    # Check for existing token
    if TOKEN_FILE.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), scopes)
            logging.debug(f"Loaded existing token from {TOKEN_FILE}")
        except Exception as e:
            logging.warning(f"Could not load existing token: {e}")
            creds = None

    # Refresh or get new credentials
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logging.info("Refreshing expired token...")
            try:
                creds.refresh(Request())
            except Exception as e:
                logging.warning(f"Token refresh failed: {e}")
                creds = None

        if not creds:
            # Need to do OAuth flow
            if not CREDENTIALS_FILE.exists():
                logging.critical(f"credentials.json not found at {CREDENTIALS_FILE}")
                logging.critical("Download from Google Cloud Console > APIs & Services > Credentials")
                raise FileNotFoundError(f"Missing credentials.json at {CREDENTIALS_FILE}")

            logging.info("Starting OAuth flow...")
            logging.info("A browser window will open for authentication.")

            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE), scopes
            )
            creds = flow.run_local_server(port=0)

            # Save the credentials for next time
            TOKEN_FILE.write_text(creds.to_json())
            logging.info(f"Saved new token to {TOKEN_FILE}")

    return creds


def get_service(service_name: str, credentials=None):
    """
    Get a Google API service client.

    Args:
        service_name: Name of service ('classroom', 'docs', 'drive')
        credentials: Optional pre-obtained credentials. If None, will get credentials.

    Returns:
        Google API service resource

    Raises:
        ValueError: If service_name is unknown
    """
    try:
        from googleapiclient.discovery import build
    except ImportError as e:
        logging.critical(f"Missing required package: {e}")
        logging.critical("Install with: pip install google-api-python-client")
        sys.exit(1)

    if service_name not in SERVICE_VERSIONS:
        raise ValueError(f"Unknown service: {service_name}. Available: {list(SERVICE_VERSIONS.keys())}")

    if credentials is None:
        credentials = get_credentials([service_name])

    api_name, api_version = SERVICE_VERSIONS[service_name]
    service = build(api_name, api_version, credentials=credentials)
    logging.debug(f"Built {service_name} service (v{api_version})")

    return service


def test_authentication():
    """Test that authentication works and print account info."""
    logging.info("Testing Google API authentication...")

    try:
        creds = get_credentials(['classroom'])
        classroom = get_service('classroom', creds)

        # Try to list courses
        results = classroom.courses().list(pageSize=5).execute()
        courses = results.get('courses', [])

        logging.info(f"Authentication successful!")
        logging.info(f"Found {len(courses)} courses:")
        for course in courses:
            logging.info(f"  - {course.get('name')} ({course.get('id')})")

        return True

    except Exception as e:
        logging.error(f"Authentication test failed: {e}")
        return False


if __name__ == "__main__":
    test_authentication()
