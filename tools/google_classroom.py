#!/usr/bin/env python3
"""
Google Classroom API Wrapper for FEA

Provides high-level functions for creating and managing Google Classroom
coursework for the Future Educators Academy.

Usage:
    from google_classroom import ClassroomClient

    client = ClassroomClient()

    # List courses
    courses = client.list_courses()

    # Create an assignment with an attached Google Doc
    assignment = client.create_assignment(
        course_id="123456789",
        title="Lesson Plan: Counting to 10",
        description="Plan a hands-on counting lesson for kindergarten.",
        due_date="2025-02-01",
        doc_content="# Lesson Plan Template\n\n## Objective\n..."
    )
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from google_auth import get_credentials, get_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)


class ClassroomClient:
    """High-level Google Classroom API client."""

    def __init__(self):
        """Initialize with authenticated Google API services."""
        logging.info("Initializing Google Classroom client...")
        self.creds = get_credentials(['classroom', 'docs', 'drive'])
        self.classroom = get_service('classroom', self.creds)
        self.docs = get_service('docs', self.creds)
        self.drive = get_service('drive', self.creds)
        logging.info("Google Classroom client ready.")

    def list_courses(self, teacher_id: str = 'me') -> list[dict]:
        """
        List all courses for the authenticated user.

        Args:
            teacher_id: Teacher ID or 'me' for current user

        Returns:
            List of course dictionaries
        """
        courses = []
        page_token = None

        while True:
            response = self.classroom.courses().list(
                teacherId=teacher_id,
                pageSize=50,
                pageToken=page_token
            ).execute()

            courses.extend(response.get('courses', []))
            page_token = response.get('nextPageToken')

            if not page_token:
                break

        logging.info(f"Found {len(courses)} courses")
        return courses

    def get_course_by_name(self, name: str) -> Optional[dict]:
        """
        Find a course by name (case-insensitive partial match).

        Args:
            name: Course name to search for

        Returns:
            Course dictionary or None if not found
        """
        courses = self.list_courses()
        name_lower = name.lower()

        for course in courses:
            if name_lower in course.get('name', '').lower():
                return course

        return None

    def create_google_doc(self, title: str, content: str, folder_id: Optional[str] = None) -> dict:
        """
        Create a Google Doc with formatted content.

        Lines ending with a colon are treated as section headers and made bold.

        Args:
            title: Document title
            content: Plain text content (lines ending in : become bold headers)
            folder_id: Optional Drive folder ID to place the doc

        Returns:
            Dictionary with 'id' and 'url' of created document
        """
        logging.info(f"Creating Google Doc: {title}")

        # Create the document
        doc = self.docs.documents().create(body={'title': title}).execute()
        doc_id = doc['documentId']
        logging.debug(f"Created doc with ID: {doc_id}")

        if content:
            # First, insert all text
            requests = [
                {
                    'insertText': {
                        'location': {'index': 1},
                        'text': content
                    }
                }
            ]
            self.docs.documents().batchUpdate(
                documentId=doc_id,
                body={'requests': requests}
            ).execute()

            # Now find and format headers (lines that are section titles)
            # Get the document to find text positions
            doc_content = self.docs.documents().get(documentId=doc_id).execute()
            body_content = doc_content.get('body', {}).get('content', [])

            format_requests = []
            for element in body_content:
                if 'paragraph' in element:
                    para = element['paragraph']
                    for elem in para.get('elements', []):
                        if 'textRun' in elem:
                            text = elem['textRun'].get('content', '')
                            start = elem.get('startIndex', 0)
                            end = elem.get('endIndex', 0)

                            # Make section headers bold (lines that look like headers)
                            stripped = text.strip()
                            if stripped and not stripped.startswith('_') and not stripped.startswith('-'):
                                # Check if it's a short line that looks like a header
                                if len(stripped) < 60 and stripped.endswith(':'):
                                    format_requests.append({
                                        'updateTextStyle': {
                                            'range': {'startIndex': start, 'endIndex': end - 1},
                                            'textStyle': {'bold': True},
                                            'fields': 'bold'
                                        }
                                    })

            if format_requests:
                self.docs.documents().batchUpdate(
                    documentId=doc_id,
                    body={'requests': format_requests}
                ).execute()

        # Move to folder if specified
        if folder_id:
            self.drive.files().update(
                fileId=doc_id,
                addParents=folder_id,
                fields='id, parents'
            ).execute()

        doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
        logging.info(f"Created Google Doc: {doc_url}")

        return {
            'id': doc_id,
            'url': doc_url,
            'title': title
        }

    def find_student_by_name(self, course_id: str, name: str) -> Optional[dict]:
        """
        Find a student by name (partial match, case-insensitive).

        Args:
            course_id: Google Classroom course ID
            name: Student name to search for

        Returns:
            Student dictionary or None if not found
        """
        students = self.list_students(course_id)
        name_lower = name.lower()

        for student in students:
            profile = student.get('profile', {})
            full_name = profile.get('name', {}).get('fullName', '')
            if name_lower in full_name.lower():
                return student

        return None

    def create_assignment(
        self,
        course_id: str,
        title: str,
        description: str,
        due_date: Optional[str] = None,
        due_time: str = "23:59:00",
        doc_title: Optional[str] = None,
        doc_content: Optional[str] = None,
        max_points: int = 100,
        state: str = 'PUBLISHED',
        student_ids: Optional[list[str]] = None
    ) -> dict:
        """
        Create a Google Classroom assignment, optionally with an attached Google Doc.

        Args:
            course_id: Google Classroom course ID
            title: Assignment title
            description: Assignment description/instructions
            due_date: Due date in YYYY-MM-DD format (optional)
            due_time: Due time in HH:MM:SS format (default 23:59:00)
            doc_title: Title for attached Google Doc (optional)
            doc_content: Content for attached Google Doc (optional)
            max_points: Maximum points for assignment (default 100)
            state: 'PUBLISHED' or 'DRAFT' (default 'PUBLISHED')
            student_ids: List of student user IDs to assign to (optional, assigns to all if None)

        Returns:
            Created coursework dictionary
        """
        logging.info(f"Creating assignment: {title}")

        # Build coursework body
        coursework = {
            'title': title,
            'description': description,
            'maxPoints': max_points,
            'workType': 'ASSIGNMENT',
            'state': state,
        }

        # Assign to specific students if provided
        if student_ids:
            coursework['assigneeMode'] = 'INDIVIDUAL_STUDENTS'
            coursework['individualStudentsOptions'] = {
                'studentIds': student_ids
            }
            logging.info(f"  Assigning to {len(student_ids)} specific student(s)")

        # Add due date if provided
        if due_date:
            year, month, day = map(int, due_date.split('-'))
            hour, minute, second = map(int, due_time.split(':'))

            coursework['dueDate'] = {
                'year': year,
                'month': month,
                'day': day
            }
            coursework['dueTime'] = {
                'hours': hour,
                'minutes': minute,
                'seconds': second
            }

        # Create and attach Google Doc if content provided
        materials = []
        if doc_content:
            doc_title = doc_title or f"{title} - Document"
            doc = self.create_google_doc(doc_title, doc_content)
            materials.append({
                'driveFile': {
                    'driveFile': {
                        'id': doc['id'],
                        'title': doc['title']
                    },
                    'shareMode': 'STUDENT_COPY'  # Each student gets their own copy
                }
            })

        if materials:
            coursework['materials'] = materials

        # Create the assignment
        result = self.classroom.courses().courseWork().create(
            courseId=course_id,
            body=coursework
        ).execute()

        assignment_url = result.get('alternateLink', '')
        logging.info(f"Created assignment: {assignment_url}")

        return result

    def list_students(self, course_id: str) -> list[dict]:
        """
        List all students in a course.

        Args:
            course_id: Google Classroom course ID

        Returns:
            List of student dictionaries
        """
        students = []
        page_token = None

        while True:
            response = self.classroom.courses().students().list(
                courseId=course_id,
                pageSize=50,
                pageToken=page_token
            ).execute()

            students.extend(response.get('students', []))
            page_token = response.get('nextPageToken')

            if not page_token:
                break

        return students

    def list_assignments(self, course_id: str) -> list[dict]:
        """
        List all assignments in a course.

        Args:
            course_id: Google Classroom course ID

        Returns:
            List of coursework dictionaries
        """
        assignments = []
        page_token = None

        while True:
            response = self.classroom.courses().courseWork().list(
                courseId=course_id,
                pageSize=50,
                pageToken=page_token
            ).execute()

            assignments.extend(response.get('courseWork', []))
            page_token = response.get('nextPageToken')

            if not page_token:
                break

        return assignments

    def get_assignment(self, course_id: str, assignment_id: str) -> dict:
        """
        Get a specific assignment by ID.

        Args:
            course_id: Google Classroom course ID
            assignment_id: Assignment (coursework) ID

        Returns:
            Coursework dictionary
        """
        return self.classroom.courses().courseWork().get(
            courseId=course_id,
            id=assignment_id
        ).execute()

    def update_assignment(
        self,
        course_id: str,
        assignment_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        materials: Optional[list] = None
    ) -> dict:
        """
        Update an existing assignment.

        Args:
            course_id: Google Classroom course ID
            assignment_id: Assignment (coursework) ID
            title: New title (optional)
            description: New description (optional)
            materials: New materials list (optional) - REPLACES existing materials

        Returns:
            Updated coursework dictionary
        """
        logging.info(f"Updating assignment {assignment_id}...")

        update_mask = []
        body = {}

        if title is not None:
            body['title'] = title
            update_mask.append('title')

        if description is not None:
            body['description'] = description
            update_mask.append('description')

        if materials is not None:
            body['materials'] = materials
            update_mask.append('materials')

        if not update_mask:
            logging.warning("No fields to update")
            return self.get_assignment(course_id, assignment_id)

        result = self.classroom.courses().courseWork().patch(
            courseId=course_id,
            id=assignment_id,
            updateMask=','.join(update_mask),
            body=body
        ).execute()

        logging.info(f"Updated assignment: {result.get('alternateLink', 'N/A')}")
        return result

    def add_material_to_assignment(
        self,
        course_id: str,
        assignment_id: str,
        doc_title: str,
        doc_content: str
    ) -> dict:
        """
        Add a Google Doc as material to an existing assignment.

        Args:
            course_id: Google Classroom course ID
            assignment_id: Assignment (coursework) ID
            doc_title: Title for the new Google Doc
            doc_content: Content for the Google Doc

        Returns:
            Updated coursework dictionary
        """
        logging.info(f"Adding material to assignment {assignment_id}...")

        # Get existing assignment
        assignment = self.get_assignment(course_id, assignment_id)
        existing_materials = assignment.get('materials', [])

        # Create the new Google Doc
        doc = self.create_google_doc(doc_title, doc_content)

        # Add new material to existing materials
        new_material = {
            'driveFile': {
                'driveFile': {
                    'id': doc['id'],
                    'title': doc['title']
                },
                'shareMode': 'STUDENT_COPY'
            }
        }
        updated_materials = existing_materials + [new_material]

        # Update the assignment
        return self.update_assignment(
            course_id=course_id,
            assignment_id=assignment_id,
            materials=updated_materials
        )


def test_classroom_client():
    """Test the Classroom client."""
    logging.info("Testing Google Classroom client...")

    try:
        client = ClassroomClient()

        # List courses
        courses = client.list_courses()
        if courses:
            print("\nAvailable courses:")
            for course in courses:
                print(f"  - {course['name']} (ID: {course['id']})")
                print(f"    State: {course.get('courseState', 'UNKNOWN')}")
        else:
            print("\nNo courses found. Create a course in Google Classroom first.")

        return True

    except Exception as e:
        logging.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    test_classroom_client()
