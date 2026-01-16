#!/usr/bin/env python3
"""
Update FEA Assignments with Meta-Lesson Attachments

Edits existing Google Classroom assignments IN PLACE to:
1. Attach meta-lesson content as a separate Google Doc
2. Update the description to remove GitHub Pages links

Usage:
    python update_fea_assignments.py --test
    python update_fea_assignments.py --execute
"""

import argparse
import logging
import re
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from google_classroom import ClassroomClient


# Assignment IDs from existing assignments
ASSIGNMENTS = [
    {
        "student_name": "Chloe Pedrotti",
        "course_id": "835379874594",
        "assignment_id": "839987608312",
        "meta_lesson_file": Path(__file__).parent.parent / "docs/fea-lessons/kindergarten/picture-book-read-aloud.md",
        "meta_lesson_title": "FEA Meta-Lesson: Reading Picture Books with Kindergartners",
    },
    {
        "student_name": "Camila Vega",
        "course_id": "835379874594",
        "assignment_id": "840002557727",
        "meta_lesson_file": Path(__file__).parent.parent / "docs/fea-lessons/grade3/helping-with-fractions.md",
        "meta_lesson_title": "FEA Meta-Lesson: Helping Third Graders Understand Fractions",
    }
]


def markdown_to_plain_text(md_content: str) -> str:
    """
    Convert markdown to plain text suitable for Google Docs.

    Removes YAML frontmatter and markdown formatting while preserving structure.
    """
    # Remove YAML frontmatter
    content = re.sub(r'^---\n.*?\n---\n', '', md_content, flags=re.DOTALL)

    # Convert headers to plain text with colons (for bold formatting)
    content = re.sub(r'^#{1,6}\s+(.+)$', r'\1:', content, flags=re.MULTILINE)

    # Remove bold/italic markers
    content = re.sub(r'\*\*(.+?)\*\*', r'\1', content)
    content = re.sub(r'\*(.+?)\*', r'\1', content)

    # Convert bullet points to dashes
    content = re.sub(r'^\s*[-*]\s+', '- ', content, flags=re.MULTILINE)

    # Convert numbered lists
    content = re.sub(r'^\s*\d+\.\s+', '', content, flags=re.MULTILINE)

    # Remove code blocks
    content = re.sub(r'```.*?```', '', content, flags=re.DOTALL)
    content = re.sub(r'`(.+?)`', r'\1', content)

    # Clean up multiple blank lines
    content = re.sub(r'\n{3,}', '\n\n', content)

    return content.strip()


def remove_github_links(description: str) -> str:
    """Remove GitHub Pages links from assignment description."""
    # Remove the meta-lesson link paragraphs
    patterns = [
        r'Read the FEA Meta-Lesson First\n\n.*?https://brian-edwards\.github\.io/elementary/[^\n]+\n\n',
        r'Before you plan anything, read through the meta-lesson.*?https://brian-edwards\.github\.io/elementary/[^\n]+\n\n',
        r'https://brian-edwards\.github\.io/elementary/[^\s]+',
    ]

    result = description
    for pattern in patterns:
        result = re.sub(pattern, '', result, flags=re.DOTALL)

    return result


def update_assignments(client: ClassroomClient, dry_run: bool = True):
    """
    Update existing assignments with meta-lesson attachments.

    Note: Google Classroom API doesn't allow adding materials to existing
    assignments. Instead, we create the Google Doc, make it accessible,
    and add a link to it in the description.

    Args:
        client: Initialized ClassroomClient
        dry_run: If True, only print what would be done
    """
    logging.info(f"Updating {len(ASSIGNMENTS)} assignments...")
    logging.info(f"Dry run: {dry_run}")
    logging.info("")

    for i, assignment_info in enumerate(ASSIGNMENTS, 1):
        student = assignment_info['student_name']
        course_id = assignment_info['course_id']
        assignment_id = assignment_info['assignment_id']
        meta_lesson_file = assignment_info['meta_lesson_file']
        meta_lesson_title = assignment_info['meta_lesson_title']

        logging.info(f"[{i}/{len(ASSIGNMENTS)}] {student}")
        logging.info(f"  Course ID: {course_id}")
        logging.info(f"  Assignment ID: {assignment_id}")

        # Read meta-lesson content
        if not meta_lesson_file.exists():
            logging.critical(f"  Meta-lesson file not found: {meta_lesson_file}")
            raise FileNotFoundError(f"Missing meta-lesson: {meta_lesson_file}")

        md_content = meta_lesson_file.read_text(encoding='utf-8')
        plain_content = markdown_to_plain_text(md_content)
        logging.info(f"  Meta-lesson: {meta_lesson_title}")
        logging.info(f"  Content length: {len(plain_content)} chars")

        if dry_run:
            logging.info("  [DRY RUN] Would:")
            logging.info(f"    - Create Google Doc: {meta_lesson_title}")
            logging.info(f"    - Make doc viewable by anyone with link")
            logging.info(f"    - Update description with link to meta-lesson doc")
            logging.info("")
            continue

        # Get existing assignment
        existing = client.get_assignment(course_id, assignment_id)
        logging.info(f"  Found assignment: {existing.get('title')}")

        # Create the meta-lesson Google Doc
        logging.info(f"  Creating meta-lesson Google Doc...")
        doc = client.create_google_doc(meta_lesson_title, plain_content)
        doc_url = doc['url']
        logging.info(f"  Created: {doc_url}")

        # Make the doc accessible (viewable by anyone with link)
        logging.info("  Setting doc permissions (anyone with link can view)...")
        client.drive.permissions().create(
            fileId=doc['id'],
            body={
                'type': 'anyone',
                'role': 'reader'
            }
        ).execute()

        # Update description to remove GitHub links and add meta-lesson doc link
        old_description = existing.get('description', '')
        new_description = remove_github_links(old_description)

        # Add link to meta-lesson doc at the appropriate place
        meta_lesson_section = f"""Read the FEA Meta-Lesson First

Before you plan anything, read through the meta-lesson we created for this assignment. It explains the research behind this approach and walks through the techniques step by step:
{doc_url}

"""
        # Insert before "What to Do Before Your Session"
        if "What to Do Before Your Session" in new_description:
            new_description = new_description.replace(
                "What to Do Before Your Session",
                meta_lesson_section + "What to Do Before Your Session"
            )
        else:
            # Fallback: add at the beginning after first paragraph
            paragraphs = new_description.split('\n\n')
            if len(paragraphs) > 2:
                paragraphs.insert(2, meta_lesson_section.strip())
                new_description = '\n\n'.join(paragraphs)

        # Update the assignment description
        logging.info("  Updating assignment description...")
        result = client.update_assignment(
            course_id=course_id,
            assignment_id=assignment_id,
            description=new_description
        )

        logging.info(f"  Updated: {result.get('alternateLink', 'N/A')}")
        logging.info("")

    logging.info("=" * 60)
    if dry_run:
        logging.info("DRY RUN COMPLETE - No changes made")
    else:
        logging.info("UPDATE COMPLETE")
    logging.info("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Update FEA assignments with meta-lesson attachments"
    )

    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually make changes (default is dry run)"
    )

    args = parser.parse_args()

    logging.info("Initializing Google Classroom client...")
    client = ClassroomClient()

    dry_run = not args.execute
    if dry_run:
        logging.info("DRY RUN MODE - Use --execute to make changes")

    update_assignments(client, dry_run=dry_run)


if __name__ == "__main__":
    main()
