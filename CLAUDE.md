# CLAUDE.md - Elementary Curriculum Development Guide

## Project Purpose

This repository manages curriculum materials from multiple educational sources (starting with Bluebonnet Learning from Texas) and generates lesson plans from those materials.

## Project Structure

```
elementary/
├── CLAUDE.md                    # This file - project guide
├── tools/                       # Tooling and scripts
│   ├── canvas_downloader.py     # Canvas LMS file downloader
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
└── docs/                        # Documentation
    └── BLUEBONNET_SPIDER.md    # Canvas download process docs
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

### 3. Review Downloaded Materials

Materials are organized in `sources/bluebonnet/` by course name and folder structure.

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

## Notes

- Downloaded materials are copyrighted; respect usage terms
- Store credentials in environment variables, not in code
- The downloader skips existing files, making incremental updates efficient
