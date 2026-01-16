#!/usr/bin/env python3
"""
PDF to Markdown Converter for Bluebonnet Learning Curriculum

Converts PDF files to LLM-optimized markdown format using pymupdf4llm.
Uses flattened output paths to avoid Windows 260 character path limit.

Usage:
    python pdf_to_markdown.py --input ../sources/bluebonnet --output ../docs/curriculum
    python pdf_to_markdown.py --input ../sources/bluebonnet --output ../docs/curriculum --workers 4
    python pdf_to_markdown.py --input ../sources/bluebonnet --output ../docs/curriculum --test -v
"""

import argparse
import logging
import re
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Configure logging
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
LOG_DATE_FORMAT = "%H:%M:%S"


def setup_logging(verbose: bool = False, log_file: Optional[Path] = None):
    """Configure logging to both console and optional file."""
    level = logging.DEBUG if verbose else logging.INFO

    handlers = [logging.StreamHandler(sys.stdout)]
    if log_file:
        handlers.append(logging.FileHandler(log_file, mode='a', encoding='utf-8'))

    logging.basicConfig(
        level=level,
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
        handlers=handlers
    )


def extract_course_code(course_path: str) -> str:
    """
    Extract abbreviated course code from full course name.

    Examples:
        "Bluebonnet Learning Grade K Foundational Skills, Edition 1" -> "GK-FS"
        "Bluebonnet Learning Grade 1 Math, Edition 1" -> "G1-Math"
        "Bluebonnet Learning Grade 4 Reading Language Arts, Edition 1" -> "G4-RLA"
    """
    # Extract grade
    grade_match = re.search(r'Grade\s+(\d|K)', course_path, re.IGNORECASE)
    grade = grade_match.group(1) if grade_match else "X"

    # Extract subject
    subject = "Unknown"
    path_lower = course_path.lower()
    if 'foundational skills' in path_lower or 'foundational' in path_lower:
        subject = "FS"
    elif 'math' in path_lower:
        subject = "Math"
    elif 'reading language arts' in path_lower or 'rla' in path_lower:
        subject = "RLA"
    elif 'knowledge' in path_lower:
        subject = "Know"
    elif 'writing' in path_lower:
        subject = "Write"

    return f"G{grade}-{subject}"


def sanitize_filename(name: str, max_length: int = 80) -> str:
    """
    Sanitize a filename for Windows compatibility.

    - Removes/replaces invalid characters
    - Truncates to max_length
    - Removes leading/trailing spaces and dots
    """
    # Replace invalid Windows filename characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        name = name.replace(char, '_')

    # Replace multiple spaces/underscores with single
    name = re.sub(r'[_\s]+', '_', name)

    # Remove leading/trailing spaces, dots, underscores
    name = name.strip(' ._')

    # Truncate if too long (preserve extension if present)
    if len(name) > max_length:
        name = name[:max_length].rstrip(' ._')

    return name


def get_flattened_output_path(pdf_path: Path, input_base: Path, output_base: Path) -> Path:
    """
    Generate a flattened output path to avoid Windows path length limits.

    Input:  sources/bluebonnet/Bluebonnet Learning Grade 4.../course files/RLA G4 Unit 10.../file.pdf
    Output: docs/curriculum/G4-RLA/file.md
    """
    try:
        # Get the relative path from input base
        rel_path = pdf_path.relative_to(input_base)
        parts = rel_path.parts

        # First part should be the course name
        course_name = parts[0] if parts else "Unknown"
        course_code = extract_course_code(course_name)

        # Use just the filename (sanitized)
        filename = sanitize_filename(pdf_path.stem, max_length=80) + ".md"

        # Build flattened path: output_base / course_code / filename
        return output_base / course_code / filename

    except ValueError:
        # If relative_to fails, just use course code extraction on full path
        course_code = extract_course_code(str(pdf_path))
        filename = sanitize_filename(pdf_path.stem, max_length=80) + ".md"
        return output_base / course_code / filename


def convert_single_pdf(args: tuple) -> tuple[str, bool, int, Optional[str]]:
    """
    Convert a single PDF to Markdown. Designed for parallel execution.

    Args:
        args: Tuple of (pdf_path_str, output_path_str, force)

    Returns:
        Tuple of (filename, success, page_count, error_message)
    """
    pdf_path_str, output_path_str, force = args
    pdf_path = Path(pdf_path_str)
    output_path = Path(output_path_str)

    try:
        # Skip if output exists and not forcing
        if output_path.exists() and not force:
            return (pdf_path.name, False, 0, "SKIP")

        # Import here to avoid issues with multiprocessing
        import pymupdf4llm

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert PDF to markdown
        md_text = pymupdf4llm.to_markdown(str(pdf_path))

        # Count pages (rough estimate from page breaks or use pymupdf directly)
        import pymupdf
        doc = pymupdf.open(str(pdf_path))
        page_count = len(doc)
        doc.close()

        # Add metadata header
        header = f"""---
source_file: {pdf_path.name}
converted: {datetime.now(timezone.utc).isoformat()}
pages: {page_count}
---

"""

        # Write output
        output_path.write_text(header + md_text, encoding='utf-8')

        return (pdf_path.name, True, page_count, None)

    except Exception as e:
        return (pdf_path.name, False, 0, str(e))


def find_pdf_files(input_dir: Path) -> list[Path]:
    """Find all PDF files in input directory recursively."""
    return sorted(input_dir.rglob("*.pdf"))


def batch_convert_parallel(
    input_dir: Path,
    output_dir: Path,
    force: bool = False,
    workers: int = 4,
    test_limit: Optional[int] = None
) -> dict:
    """
    Convert all PDFs in input directory to markdown using parallel processing.

    FAIL-FAST: Stops on first error. This is intentional and required.
    """
    logging.info("")
    logging.info("=" * 60)
    logging.info("PDF TO MARKDOWN CONVERTER (PARALLEL)")
    logging.info("=" * 60)
    logging.info(f"Input:   {input_dir}")
    logging.info(f"Output:  {output_dir}")
    logging.info(f"Workers: {workers}")
    logging.info(f"Force:   {force}")
    logging.info("=" * 60)

    # Find all PDFs
    logging.info("Scanning for PDF files...")
    pdf_files = find_pdf_files(input_dir)

    if test_limit:
        pdf_files = pdf_files[:test_limit]
        logging.info(f"  TEST MODE: Limited to {test_limit} files")

    logging.info(f"  Found {len(pdf_files)} PDF files")

    if not pdf_files:
        logging.warning("No PDF files found!")
        return {"total": 0, "converted": 0, "skipped": 0, "failed": 0, "pages": 0}

    # Prepare work items
    work_items = []
    for pdf_path in pdf_files:
        output_path = get_flattened_output_path(pdf_path, input_dir, output_dir)
        work_items.append((str(pdf_path), str(output_path), force))

    # Process in parallel
    logging.info("")
    logging.info(f"Starting {workers} parallel workers...")
    logging.info("")

    stats = {"total": len(pdf_files), "converted": 0, "skipped": 0, "failed": 0, "pages": 0}
    start_time = datetime.now()
    completed = 0

    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(convert_single_pdf, item): item for item in work_items}

        for future in as_completed(futures):
            completed += 1
            filename, success, page_count, error = future.result()

            if error == "SKIP":
                stats["skipped"] += 1
                logging.debug(f"[{completed}/{stats['total']}] SKIP: {filename}")
            elif success:
                stats["converted"] += 1
                stats["pages"] += page_count
                logging.info(f"[{completed}/{stats['total']}] OK: {filename} ({page_count} pages)")
            else:
                stats["failed"] += 1
                logging.error(f"[{completed}/{stats['total']}] FAILED: {filename} - {error}")

                # FAIL-FAST: Stop on first error
                logging.critical("")
                logging.critical("=" * 60)
                logging.critical("FATAL ERROR - STOPPING")
                logging.critical("=" * 60)
                logging.critical(f"Conversion failed for {filename}: {error}")
                logging.critical("=" * 60)

                # Cancel remaining futures
                for f in futures:
                    f.cancel()

                raise RuntimeError(f"Conversion failed for {filename}: {error}")

            # Progress update every 20 files
            if completed % 20 == 0:
                elapsed = (datetime.now() - start_time).total_seconds()
                elapsed_str = f"{int(elapsed // 3600)}h {int((elapsed % 3600) // 60)}m" if elapsed > 3600 else f"{int(elapsed // 60)}m {int(elapsed % 60)}s"
                logging.info(f"Progress: {completed}/{stats['total']} ({100*completed/stats['total']:.1f}%) | Pages: {stats['pages']} | Elapsed: {elapsed_str}")

    # Final summary
    elapsed = (datetime.now() - start_time).total_seconds()
    logging.info("")
    logging.info("=" * 60)
    logging.info("CONVERSION COMPLETE")
    logging.info("=" * 60)
    logging.info(f"Total files:  {stats['total']}")
    logging.info(f"Converted:    {stats['converted']}")
    logging.info(f"Skipped:      {stats['skipped']}")
    logging.info(f"Failed:       {stats['failed']}")
    logging.info(f"Total pages:  {stats['pages']}")
    logging.info(f"Time elapsed: {elapsed:.1f} seconds")
    logging.info("=" * 60)

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Convert PDF files to LLM-optimized markdown",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Convert all PDFs with 4 workers
    python pdf_to_markdown.py --input ../sources/bluebonnet --output ../docs/curriculum --workers 4

    # Test on first 3 files with verbose output
    python pdf_to_markdown.py --input ../sources/bluebonnet --output ../docs/curriculum --test -v

    # Force overwrite existing files
    python pdf_to_markdown.py --input ../sources/bluebonnet --output ../docs/curriculum --force
"""
    )

    parser.add_argument(
        "--input", "-i",
        type=Path,
        default=Path("../sources/bluebonnet"),
        help="Input directory containing PDF files (default: ../sources/bluebonnet)"
    )

    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=Path("../docs/curriculum"),
        help="Output directory for markdown files (default: ../docs/curriculum)"
    )

    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Overwrite existing markdown files"
    )

    parser.add_argument(
        "--workers", "-w",
        type=int,
        default=4,
        help="Number of parallel workers (default: 4)"
    )

    parser.add_argument(
        "--test", "-t",
        action="store_true",
        help="Test mode: only process first 3 files"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose/debug logging"
    )

    parser.add_argument(
        "--log-file",
        type=Path,
        default=Path("../pdf_conversion.log"),
        help="Log file path (default: ../pdf_conversion.log)"
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(verbose=args.verbose, log_file=args.log_file)

    # Validate input directory
    if not args.input.exists():
        logging.critical(f"Input directory does not exist: {args.input}")
        sys.exit(1)

    # Create output directory if needed
    args.output.mkdir(parents=True, exist_ok=True)

    # Run conversion
    test_limit = 3 if args.test else None

    try:
        stats = batch_convert_parallel(
            input_dir=args.input,
            output_dir=args.output,
            force=args.force,
            workers=args.workers,
            test_limit=test_limit
        )

        if stats["failed"] > 0:
            sys.exit(1)

    except Exception as e:
        logging.critical(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
