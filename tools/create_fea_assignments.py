#!/usr/bin/env python3
"""
FEA Google Classroom Assignment Creator

Creates personalized Google Classroom assignments for Future Educators Academy
students based on their Work-Based Learning placements and mentor teacher info.

Usage:
    python create_fea_assignments.py --course "FEA Work-Based Learning" --test
    python create_fea_assignments.py --course "FEA Work-Based Learning" --publish

FAIL-FAST: This script stops on first error. This is intentional.
"""

import argparse
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from google_classroom import ClassroomClient


# ============================================================================
# STUDENT ASSIGNMENT DEFINITIONS
# ============================================================================

# Two test students selected based on mentor teachers with concrete curriculum info

ASSIGNMENTS = [
    {
        "student_name": "Pedrotti",  # Full name: Chloe Jean Pedrotti
        "mentor_teacher": "Rebecca Wakefield",
        "mentor_email": "rebecca.wakefield@wacoisd.org",
        "grade_level": "Kindergarten",
        "room": "B101",
        "subject": "Reading",
        "curriculum": "HMH Into Reading Module 5",
        "assignment_title": "Lesson Plan: Interactive Picture Book Read-Aloud",
        "assignment_description": """Chloe, this assignment prepares you to lead an interactive picture book read-aloud with Ms. Wakefield's kindergarten class in Room B101.

Your WBL Schedule with Ms. Wakefield:
Monday 8:35-10:05, Tuesday 8:30-10:00, Friday 8:30-10:00

About This Lesson

Ms. Wakefield's class is currently working through HMH Into Reading Module 5, which focuses on building independence and trying new things. The two main books are "Jabari Jumps" by Gaia Cornwall, about a boy working up the courage to jump off a diving board, and "All By Myself" by Mercer Mayer, where Little Critter learns to do things independently.

Interactive read-alouds are different from simply reading a book out loud. You will pause at strategic points to help students make predictions about what will happen next, ask questions about the story, and connect the characters' experiences to their own lives. These three comprehension skills are aligned to Texas TEKS K.5B, K.5C, and K.5E. The goal is to help kindergartners develop as active readers rather than passive listeners.

Ms. Wakefield shared some helpful information about her students: they respond well to movement and hands-on activities. Build in moments where students can do thumbs up/down, touch their head, or stand up. Keep the total read-aloud to 15-20 minutes.

How to Access the Curriculum

The HMH Into Reading curriculum is accessed through Clever:

1. Go to clever.com
2. Log in with your Waco ISD credentials
3. Find and click on "HMH Into Reading"
4. Select "Grade K" from the grade menu
5. Navigate to "Module 5"
6. Look for "Week 1" - Lesson 1 contains "Jabari Jumps" and Lesson 3 contains "All By Myself"
7. Inside each lesson, you will find the digital book, suggested discussion questions, vocabulary words, and teaching notes

What to look for in the curriculum materials: Pay attention to the "Essential Question" for the module, the vocabulary words students are learning, and the comprehension skill focus. The Teacher's Guide provides suggested stopping points and questions.

Read the FEA Meta-Lesson First

Before you plan anything, read through the meta-lesson we created for this assignment. It explains the research behind interactive read-alouds and walks through the techniques step by step:
https://brian-edwards.github.io/elementary/fea-lessons/kindergarten/picture-book-read-aloud

What to Do Before Your Session

1. Choose either "Jabari Jumps" or "All By Myself" and read it at least three times yourself
2. Mark 3-4 stopping points with sticky notes where you will pause to engage students
3. Plan one prediction question, one "I wonder" question, and one personal connection prompt
4. Plan at least one movement activity (example: "Touch your head if you think Jabari will jump!")
5. Practice reading aloud with expression
6. Complete the attached lesson plan template

Contact: rebecca.wakefield@wacoisd.org
""",
        "doc_title": "Chloe Pedrotti - Kindergarten Read-Aloud Lesson Plan",
        "doc_content": """Lesson Plan: Interactive Picture Book Read-Aloud

Student: Chloe Pedrotti
Mentor Teacher: Rebecca Wakefield (Room B101)
Grade: Kindergarten
Curriculum: HMH Into Reading Module 5


Before you start:
Read the meta-lesson first:
https://brian-edwards.github.io/elementary/fea-lessons/kindergarten/picture-book-read-aloud


Book Selection:

Which book will you read?

    Jabari Jumps by Gaia Cornwall
    All By Myself by Mercer Mayer
    Other: ____________________

Why did you choose this book?




Your Objective:

What is the one skill you want students to practice?
(pick one: making predictions, asking questions, or making connections)




Preparation Checklist:

___ I read the book at least 3 times
___ I marked stopping points with sticky notes
___ I practiced reading aloud with expression
___ I know how to hold the book so students can see pictures
___ I talked to Ms. Wakefield about the students


Your Stopping Points:

Plan 3-4 places where you will pause to engage students.

Stop 1 - Page: ____
What I will ask or say:

Skill: prediction / question / connection


Stop 2 - Page: ____
What I will ask or say:

Skill: prediction / question / connection


Stop 3 - Page: ____
What I will ask or say:

Skill: prediction / question / connection


Stop 4 - Page: ____
What I will ask or say:

Skill: prediction / question / connection


Introduction (2-3 minutes):

How will you introduce the book and build interest?



What purpose for listening will you give students?
"While I read, I want you to think about..."




Movement Break:

Ms. Wakefield says students like to move. Plan at least one movement activity.

Example: "Touch your head if you think Jabari will jump!"




Wrap-up (2-3 minutes):

What will you ask students to help them remember the story?



How will you transition them to the next activity?




After Your Lesson:

What went well?



What would you do differently next time?



What did you notice about student engagement?


"""
    },
    {
        "student_name": "Camila Vega",
        "mentor_teacher": "Marissa Templeton",
        "mentor_email": "Marissa.Templeton@wacoisd.org",
        "grade_level": "3rd Grade",
        "room": "C111",
        "subject": "Math (Fractions)",
        "curriculum": "Bluebonnet Learning Module 5 - Fractions",
        "assignment_title": "Lesson Plan: Helping with Fractions",
        "assignment_description": """Camila, this assignment prepares you to support 3rd grade students learning fractions in Ms. Templeton's math class in Room C111.

Your WBL Schedule with Ms. Templeton:
Monday 8:30-10:00, Wednesday 8:30-10:00, Thursday 8:30-10:00

Note: RLA benchmark testing is Tuesday, so students may be tired on Wednesday.

About This Lesson

Ms. Templeton's class is working through Bluebonnet Learning Module 5, which covers fractions. This week focuses on Lessons 7, 8, 9, and 11. Fractions are one of the most challenging concepts for elementary students because they require a fundamentally different way of thinking about numbers. Instead of counting whole things, students must understand that one whole can be divided into equal parts.

Your role is to work with small groups of students who need extra support. You are not teaching the whole class lesson - Ms. Templeton does that. You are helping individual students who are struggling, asking questions to check their understanding, and guiding them when they get stuck. The most important thing you can do is ask students to explain their thinking out loud. When a student says "I don't get it," ask them to show you what they do understand, then build from there.

Ms. Templeton emphasized using manipulatives - physical objects like fraction circles, fraction strips, and number lines that students can touch and move. Abstract fraction concepts become concrete when students can physically see that two halves make a whole.

How to Access the Curriculum

The Bluebonnet Learning curriculum is accessed through the TEA learning portal:

1. Go to tealearn.instructure.com
2. Log in with your Waco ISD credentials
3. Find the Bluebonnet Learning course for Grade 3 Math
4. Navigate to Module 5 (Fractions)
5. Find the specific lesson number Ms. Templeton will be teaching that day (7, 8, 9, or 11)
6. Review the Teacher Guide for that lesson - it shows the learning objective, common misconceptions, and suggested questions

What to look for: Each lesson has a clear objective. Before your session, know what students should be able to do by the end of the lesson. The Teacher Guide also lists common mistakes students make, which helps you recognize when a student is confused.

We have also converted the curriculum to our website for easier reading:
https://brian-edwards.github.io/elementary/

Read the FEA Meta-Lesson First

Before you plan anything, read through the meta-lesson we created for helping with fractions. It explains the common misconceptions students have and specific strategies for addressing them:
https://brian-edwards.github.io/elementary/fea-lessons/grade3/helping-with-fractions

Key Concepts Students Are Learning

Fractions represent equal parts of a whole. The denominator (bottom number) tells how many equal parts the whole is divided into. The numerator (top number) tells how many of those parts we are talking about. Fractions can be placed on a number line between 0 and 1. Two fractions can be equivalent, meaning they have the same value even though they look different (like 1/2 and 2/4).

Common Mistakes to Watch For

Students often think 1/4 is bigger than 1/2 because 4 is bigger than 2. They may not understand that the parts must be equal in size. They confuse which number is the numerator and which is the denominator. They struggle to see where fractions belong on a number line. When you see these mistakes, use manipulatives to make the concept visible.

What to Do Before Your Session

1. Read the meta-lesson linked above
2. Check with Ms. Templeton about which lesson she is teaching that day
3. Review that lesson in the Bluebonnet curriculum
4. Gather manipulatives you might need (fraction circles, strips, number line)
5. Complete the attached lesson plan template
6. Think about questions you will ask to check understanding

Contact: Marissa.Templeton@wacoisd.org
""",
        "doc_title": "Camila Vega - 3rd Grade Fractions Lesson Plan",
        "doc_content": """Lesson Plan: Helping with Fractions

Student: Camila Vega
Mentor Teacher: Marissa Templeton (Room C111)
Grade: 3rd
Curriculum: Bluebonnet Module 5 - Fractions


Before you start:

Read the meta-lesson first:
https://brian-edwards.github.io/elementary/fea-lessons/grade3/helping-with-fractions


Which lesson?

Which Module 5 lesson will you be supporting?

    Lesson 7
    Lesson 8
    Lesson 9
    Lesson 11

What is the main concept in this lesson?




Understanding student thinking:

What mistakes might students make with this topic?



How will you check if students are confused?




Materials:

Check what you need and confirm with Ms. Templeton:

___ Fraction circles
___ Fraction strips/bars
___ Number line
___ Whiteboard/markers for student work
___ Worksheet from curriculum

Do you need to make any visual aids?




Questions to ask:

Write 3 questions that help students think (not just give answers):

Question 1 (to check understanding):


Question 2 (to push thinking deeper):


Question 3 (to help when stuck):




Worked example:

Write out one example problem you might work through with students:

Problem:


Step-by-step solution:


Questions to ask during the example:




When students struggle:

If a student says 1/4 is bigger than 1/2, what will you do?



If a student can't find a fraction on the number line, what will you do?



If a student doesn't understand "equal parts," what will you do?




After your lesson:

What fraction concepts did students understand well?


What was still confusing?


What would you do differently?


What did you learn about teaching math?


"""
    }
]


def create_test_assignments(client: ClassroomClient, course_id: str, dry_run: bool = True):
    """
    Create test assignments for FEA students.

    FAIL-FAST: Stops on first error.

    Args:
        client: Initialized ClassroomClient
        course_id: Google Classroom course ID
        dry_run: If True, only print what would be created
    """
    logging.info(f"Creating {len(ASSIGNMENTS)} assignments...")
    logging.info(f"Course ID: {course_id}")
    logging.info(f"Dry run: {dry_run}")
    logging.info("")

    created = []

    for i, assignment in enumerate(ASSIGNMENTS, 1):
        student_name = assignment['student_name']
        logging.info(f"[{i}/{len(ASSIGNMENTS)}] {student_name}")
        logging.info(f"  Title: {assignment['assignment_title']}")
        logging.info(f"  Mentor: {assignment['mentor_teacher']} ({assignment['grade_level']})")

        # Find the student in the course - REQUIRED
        student = client.find_student_by_name(course_id, student_name)
        if not student:
            logging.critical(f"  FAILED: Student '{student_name}' not found in course!")
            logging.critical("  Check that the student is enrolled in this course.")
            raise RuntimeError(f"Student '{student_name}' not found in course")

        student_id = student.get('userId')
        student_full_name = student.get('profile', {}).get('name', {}).get('fullName', 'Unknown')
        logging.info(f"  Found student: {student_full_name} (ID: {student_id})")

        if dry_run:
            logging.info("  [DRY RUN] Would create assignment for this student only")
            logging.info("")
            continue

        # Create the assignment for this specific student only
        try:
            result = client.create_assignment(
                course_id=course_id,
                title=assignment['assignment_title'],
                description=assignment['assignment_description'],
                doc_title=assignment['doc_title'],
                doc_content=assignment['doc_content'],
                max_points=100,
                state='PUBLISHED',
                student_ids=[student_id]  # Assign to this student ONLY
            )

            created.append({
                'student': assignment['student_name'],
                'assignment_id': result['id'],
                'url': result.get('alternateLink', 'N/A')
            })

            logging.info(f"  Created: {result.get('alternateLink', 'N/A')}")
            logging.info("")

        except Exception as e:
            # FAIL-FAST: Stop on error
            logging.critical(f"FAILED to create assignment for {assignment['student_name']}")
            logging.critical(f"Error: {e}")
            raise RuntimeError(f"Assignment creation failed: {e}")

    # Summary
    logging.info("=" * 60)
    if dry_run:
        logging.info("DRY RUN COMPLETE - No assignments were created")
        logging.info(f"Would have created {len(ASSIGNMENTS)} assignments")
    else:
        logging.info("ASSIGNMENT CREATION COMPLETE")
        logging.info(f"Created {len(created)} assignments:")
        for c in created:
            logging.info(f"  - {c['student']}: {c['url']}")
    logging.info("=" * 60)

    return created


def main():
    parser = argparse.ArgumentParser(
        description="Create FEA Google Classroom assignments",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "--course", "-c",
        type=str,
        help="Course name or ID to create assignments in (required unless --list-courses)"
    )

    parser.add_argument(
        "--publish",
        action="store_true",
        help="Actually publish assignments (default is dry run)"
    )

    parser.add_argument(
        "--list-courses",
        action="store_true",
        help="List available courses and exit"
    )

    args = parser.parse_args()

    # Initialize client
    logging.info("Initializing Google Classroom client...")
    client = ClassroomClient()

    # List courses if requested
    if args.list_courses:
        courses = client.list_courses()
        print("\nAvailable courses:")
        print("(Courses with 'Lovelace' are marked - DO NOT USE)")
        print()
        for course in courses:
            state = course.get('courseState', 'UNKNOWN')
            name = course['name']
            is_lovelace = 'lovelace' in name.lower()
            marker = " [DO NOT USE - Lovelace]" if is_lovelace else ""
            print(f"  {name}{marker}")
            print(f"    ID: {course['id']}")
            print(f"    State: {state}")
            print()
        return

    # Validate --course is provided when not listing
    if not args.course:
        logging.critical("--course is required (unless using --list-courses)")
        sys.exit(1)

    # Find course
    course_id = args.course
    course_name = args.course
    if not course_id.isdigit():
        # Search by name
        logging.info(f"Searching for course: {args.course}")
        course = client.get_course_by_name(args.course)
        if not course:
            logging.critical(f"Course not found: {args.course}")
            logging.critical("Use --list-courses to see available courses")
            sys.exit(1)
        course_id = course['id']
        course_name = course['name']
        logging.info(f"Found course: {course_name} (ID: {course_id})")

    # CRITICAL: Never use Lovelace classrooms
    if 'lovelace' in course_name.lower():
        logging.critical("=" * 60)
        logging.critical("BLOCKED: Cannot use Lovelace classrooms!")
        logging.critical("=" * 60)
        logging.critical(f"Course '{course_name}' contains 'Lovelace'")
        logging.critical("Use --list-courses to find a non-Lovelace classroom")
        logging.critical("=" * 60)
        sys.exit(1)

    # Create assignments
    dry_run = not args.publish
    if dry_run:
        logging.info("DRY RUN MODE - Use --publish to actually create assignments")

    create_test_assignments(client, course_id, dry_run=dry_run)


if __name__ == "__main__":
    main()
