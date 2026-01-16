# CLAUDE.md - Elementary Curriculum Development Guide

## Project Purpose

This repository supports the **Future Educators Academy (FEA)** at Waco ISD P-TECH, where high school students (grades 9-12) learn to become teachers through Work-Based Learning (WBL). The FEA students come from Waco High School and University High School to South Waco Elementary for half-day sessions, where they prepare and deliver lessons to elementary students (Pre-K through 5th grade) under the guidance of elementary teachers.

**Key stakeholders:**
- **Brian Edwards** - High School teacher of Instructional Practices and Practicum classes
- **FEA Students** - High school students learning to teach
- **Elementary Teachers** - Mentors who guide FEA students in their classrooms
- **Elementary Students** - Pre-K to 5th grade learners

**Curriculum sources:**
- **TEA Bluebonnet** - Used for math and foundational literacy (this repository)
- **HMH via Clever** - Used for reading (separate system)

## FEA Meta-Lesson Development

The primary output of this repository is **meta-lessons** - instructional guides that teach FEA high school students how to prepare and deliver elementary lessons. These are NOT the elementary lessons themselves, but scaffolded guidance for first-time teachers.

### Meta-Lesson Requirements

When creating meta-lessons for FEA students:

1. **Accessibility**: Write at an accessible reading level. Use clear, flowing prose that works well with text-to-speech (Speechify). Vary sentence and paragraph lengths naturally.

2. **First Principles**: Explain concepts from the ground up. Differentiate similar concepts and contrast with opposites. Avoid educational jargon - when technical terms are necessary, define them clearly.

3. **Navigation Guidance**: Include specific instructions for finding source materials:
   - How to log into tealearn.instructure.com
   - Exact navigation path to relevant curriculum files
   - What to look for in the source materials

4. **Pedagogy Connections**: Connect each lesson to research-backed teaching techniques. Critique curriculum where it doesn't follow best practices and suggest alternatives.

5. **Time Constraints**:
   - Pre-K lessons: Maximum 20 minutes (state guideline)
   - K-5 lessons: 15-20 minutes typical

6. **Writing Style**:
   - Flowing text enjoyable for text-to-speech
   - Varied sentence and paragraph lengths
   - Avoid: overused terms, lots of short punchy sentences
   - Spell out acronyms on first use

### Current WBL Focus Areas

- **Phonological Awareness**: Alliteration, onset-rime
- Additional topics based on WBL schedule

### Meta-Lesson Output Structure

Meta-lessons are saved to `docs/fea-lessons/` alongside the original curriculum in `docs/curriculum/`. Each meta-lesson includes:

1. Overview for the FEA student
2. Where to find the source material (navigation instructions)
3. Key concepts explained from first principles
4. Research-backed techniques demonstrated in this lesson
5. Critique and alternatives (if applicable)
6. Step-by-step preparation guide
7. Delivery tips and common pitfalls

## Privacy Requirements

**CRITICAL**: Never include student Personally Identifiable Information (PII) in any files, especially those deployed to GitHub Pages. This includes:
- Student names
- Student IDs
- Grades or assessment scores
- Any identifying information

## Project Structure

```
elementary/
├── CLAUDE.md                    # This file - project guide
├── tools/                       # Tooling and scripts
│   ├── canvas_downloader.py     # Canvas LMS file downloader
│   ├── pdf_to_markdown.py       # PDF to markdown converter
│   ├── test_canvas_downloader.py # Tests for the downloader
│   └── requirements.txt         # Python dependencies
├── sources/                     # Source curriculum materials
│   ├── bluebonnet/             # Bluebonnet Learning (TEA/Texas)
│   │   ├── manifest.json       # Catalog of all downloaded files
│   │   └── [Course Name]/      # One folder per course
│   │       └── course files/   # Organized by Canvas folder structure
│   └── [future_sources]/       # Other curriculum sources (future)
├── lesson_plans/                # Generated lesson plans
│   ├── drafts/                 # Work-in-progress plans
│   └── final/                  # Completed, reviewed plans
├── docs/                        # GitHub Pages site & documentation
│   ├── _config.yml             # Jekyll configuration
│   ├── index.md                # Site homepage
│   ├── ai-tips.md              # AI assistant usage guide
│   ├── curriculum/             # Converted markdown curriculum
│   │   └── [course folders]/   # Organized by course/unit
│   └── BLUEBONNET_SPIDER.md    # Canvas download process docs
└── README.md                    # Project readme
```

## Getting Started

### 1. Install Dependencies

```bash
cd tools
pip install -r requirements.txt
```

### 2. Download Source Materials

```bash
cd tools

# First, generate a manifest to see what's available
python canvas_downloader.py --manifest-only

# Then download all files
python canvas_downloader.py

# Or download a specific course
python canvas_downloader.py --course 9564
```

### 3. Convert PDFs to Markdown

```bash
cd tools

# Test conversion on first 3 files
python pdf_to_markdown.py --input ../sources/bluebonnet --output ../docs/curriculum --test -v

# Convert all PDFs
python pdf_to_markdown.py --input ../sources/bluebonnet --output ../docs/curriculum -v

# Force overwrite existing files
python pdf_to_markdown.py --input ../sources/bluebonnet --output ../docs/curriculum --force
```

### 4. Review Materials

- **Raw PDFs**: `sources/bluebonnet/` organized by course and folder
- **Markdown**: `docs/curriculum/` for AI-assisted work
- **Online**: GitHub Pages site (if deployed)

## Working with Curriculum Materials

### Bluebonnet Learning Organization

Bluebonnet Learning courses follow a consistent naming pattern:
- **Grade Level**: K, 1, 2, 3, 4, 5
- **Subject Area**: Foundational Skills (FS), Knowledge (K), Writing
- **Edition**: Edition 1

Example: `Bluebonnet Learning Grade 2 Foundational Skills, Edition 1`

### File Types

| Extension | Content Type | Usage |
|-----------|--------------|-------|
| `.pdf` | Lessons, readers, assessments | Primary instructional materials |
| `.docx` | Editable templates | Teacher planning documents |
| `.pptx` | Presentations | Classroom instruction slides |
| `.mp3/.mp4` | Audio/video | Multimedia resources |
| `.zip` | Bundled resources | Collections of related files |

### Folder Naming Conventions

Within each course, folders follow patterns like:
- `RLA FS GK Course-Level Documents/` - Course-wide resources
- `RLA FS GK Program-Level Resources/` - Program-wide materials
- `RLA FS1 GK/` - Unit 1 materials (FS1 = Foundational Skills Unit 1)
- `RLA FS2 GK/` - Unit 2 materials, etc.

## Lesson Plan Development

### Workflow

1. **Identify Target Grade/Subject**: Navigate to the relevant course in `sources/`
2. **Review Course-Level Documents**: Start with overview materials
3. **Examine Unit Structure**: Each FSx folder contains unit-specific content
4. **Cross-Reference Standards**: Align with TEKS (Texas Essential Knowledge and Skills)
5. **Generate Lesson Plans**: Save drafts to `lesson_plans/drafts/`
6. **Review and Finalize**: Move completed plans to `lesson_plans/final/`

### Lesson Plan Template

When creating lesson plans, use this structure:

```markdown
# Lesson Plan: [Topic]

## Metadata
- **Grade**: [K-5]
- **Subject**: [Foundational Skills / Knowledge / Writing]
- **Unit**: [Unit Number]
- **Duration**: [Estimated time]
- **Source Files**: [List of referenced PDFs/materials]

## Learning Objectives
- Students will be able to...

## TEKS Alignment
- [Relevant Texas standards]

## Materials Needed
- [List from downloaded resources]

## Lesson Sequence

### Opening (X minutes)
-

### Direct Instruction (X minutes)
-

### Guided Practice (X minutes)
-

### Independent Practice (X minutes)
-

### Closing (X minutes)
-

## Assessment
-

## Differentiation
- **Support**:
- **Extension**:

## Notes
-
```

## Commands Reference

### Downloading Materials

```bash
# From the tools/ directory:

# Test API connectivity
python canvas_downloader.py --test

# Generate manifest only (catalog without downloading)
python canvas_downloader.py --manifest-only

# Download all courses
python canvas_downloader.py

# Download specific course
python canvas_downloader.py --course 9564

# Custom output directory
python canvas_downloader.py --output ../sources/other_source

# With API token (or set CANVAS_API_TOKEN env var)
python canvas_downloader.py --token YOUR_TOKEN
```

### Running Tests

```bash
cd tools

# Run all unit tests
pytest test_canvas_downloader.py -v

# Run integration tests (requires CANVAS_API_TOKEN)
CANVAS_API_TOKEN=your_token pytest test_canvas_downloader.py -v -m integration
```

### Searching Materials

```bash
# Find all PDFs for a specific grade
find sources/bluebonnet -path "*Grade K*" -name "*.pdf"

# List all files in a unit
ls -la "sources/bluebonnet/[Course Name]/course files/RLA FS1 GK/"

# Count files per course
find sources/bluebonnet -type f | cut -d'/' -f3 | sort | uniq -c
```

## Adding New Source Materials

To add a new curriculum source:

1. Create a new directory under `sources/`:
   ```bash
   mkdir -p sources/new_source_name
   ```

2. Either:
   - Adapt `canvas_downloader.py` for the new source's API
   - Create a new downloader script in `tools/`
   - Manually organize downloaded materials

3. Document the source in `docs/`

## Quality Checks

Before finalizing lesson plans:

- [ ] All referenced materials exist in sources/
- [ ] TEKS alignment is accurate
- [ ] Time estimates are realistic
- [ ] Differentiation options are meaningful
- [ ] Assessment aligns with objectives

## Coding Standards

### CRITICAL: Fail-Fast Error Handling

**NEVER remove fail-fast error handling from scripts.** When a script encounters an error, it MUST stop immediately rather than continuing and potentially producing corrupt or incomplete output. This is non-negotiable.

Bad (DO NOT DO THIS):
```python
try:
    process_file(f)
except Exception as e:
    logging.warning(f"Skipping {f}: {e}")
    continue  # BAD - silently continues, hiding problems
```

Good:
```python
try:
    process_file(f)
except Exception as e:
    logging.critical(f"FATAL ERROR processing {f}: {e}")
    raise  # GOOD - stops immediately, forces fix
```

### Windows Path Length Limits

Windows has a 260 character path limit. When generating output paths:

**DO:** Flatten/shorten directory structures
```
docs/curriculum/G4-RLA/Unit10-Teacher-Guide.md
```

**DON'T:** Preserve full source hierarchy with long names
```
docs/curriculum/Bluebonnet Learning Grade 4 Reading Language Arts,/course files/RLA G4 Unit 10_ Novel Study_ Number the Stars/Unit 10 Teacher Guide G4.md
```

Use abbreviated course codes:
- `GK-FS` = Grade K Foundational Skills
- `G1-Math` = Grade 1 Math
- `G4-RLA` = Grade 4 Reading Language Arts

### Logging

- Use `logging` module, not print statements
- Log to both stdout and a log file
- Include timestamps
- Use appropriate log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)

## Google Classroom

### CRITICAL: Never Use Lovelace Classrooms

**NEVER create assignments in classrooms with "Lovelace" in the name.** These are not the correct classrooms for FEA assignments. Always use non-Lovelace classrooms for FEA Work-Based Learning content.

### Course Selection Rules

When selecting a Google Classroom course for assignments:

1. **Student must be enrolled** - The HS student (from the WBL schedule) must be in the class
2. **Prefer "Instructional Practices & Practicum"** courses over "Communications and Technology"
3. **Prefer lower numbers** - Use "1 Instructional Practices & Practicum" before "3 Instructional Practices & Practicum"

### CRITICAL: Assign to Specific Students Only

**NEVER assign to the entire class.** Each assignment must be assigned ONLY to the specific student it was created for. The script automatically:
1. Finds the student by name in the course
2. Assigns the assignment to that student only (using `assigneeMode: INDIVIDUAL_STUDENTS`)
3. Fails if the student is not found in the course

### CRITICAL: Edit Assignments In Place

**NEVER create duplicate assignments.** When updating an existing assignment:
1. Use the Google Classroom API to UPDATE the existing assignment, not create a new one
2. Use the Google Docs API to UPDATE the existing attached document, not create a new one
3. If an assignment already exists for a student, modify it rather than creating another

This applies to both the assignment description and the attached Google Doc. Creating duplicates creates confusion and extra cleanup work.

### CRITICAL: Attach Meta-Lessons as Google Docs

**NEVER link to GitHub Pages for meta-lessons.** Instead:
1. Attach the meta-lesson content as a Google Doc to the assignment
2. Students should have all materials directly in Google Classroom, not external links
3. Convert the markdown meta-lesson content to a Google Doc and attach it alongside the lesson plan template

This ensures students can access everything offline and don't need to navigate to external websites.

Available courses (in order of preference):
- 1 Instructional Practices & Practicum (ID: 835379874594)
- 3 Instructional Practices & Practicum (ID: 835393083505)
- 5 Instructional Practices & Practicum (ID: 835750565592)
- 7 Instructional Practices & Practicum (ID: 835751410075)

When using `create_fea_assignments.py`:
- Use `--list-courses` to see available courses
- Select a course that does NOT contain "Lovelace"
- Verify the course name before publishing with `--publish`

## Git Workflow

### Repository

Remote: https://github.com/bme-wacoisd/elementary.git

### CRITICAL: Commit and Push Often

**Commit and push with every significant change.** Do not accumulate multiple changes before committing. This ensures:
1. Work is backed up immediately
2. Changes are visible to collaborators
3. Easy rollback if something goes wrong

After every code change, file update, or task completion:
```bash
git add -A && git commit -m "Brief description" && git push
```

## Notes

- Downloaded materials are copyrighted; respect usage terms
- Store credentials in environment variables, not in code
- The downloader skips existing files, making incremental updates efficient
