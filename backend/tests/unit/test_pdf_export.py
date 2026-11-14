"""
Unit tests for EduNex AI PDF Export Service.
Validates:
1. Short notes generation and valid PDF magic bytes (%PDF)
2. Long multi-page notes spanning multiple pages with dynamic "Page X of Y"
3. Markdown headings (H1-H4) and list formatting (unordered bullets and numbered lists)
4. Markdown tables with column formatting and cell wrapping
5. Fenced code blocks with syntax styling
6. Blockquotes / callout boxes
7. Mathematical expressions and inline notation
8. Unicode character sanitization
"""
import pytest
from app.services.pdf_service import PDFService


def test_short_notes_pdf_generation():
    """Generates a valid single-page PDF with correct headers and non-empty byte buffer."""
    title = "Introduction to Database Systems"
    subject = "Computer Science"
    content = """# Introduction to Database Systems
A database management system (DBMS) is software that manages relational or non-relational data.

## Core Properties (ACID)
- **Atomicity**: All or nothing transaction execution.
- **Consistency**: Preserves schema constraints.
- **Isolation**: Concurrently executed transactions appear sequential.
- **Durability**: Committed data survives power loss.
"""
    pdf_bytes = PDFService.generate_notes_pdf(title=title, subject=subject, content=content)

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF"), "Must start with valid PDF magic bytes %PDF"
    assert b"%%EOF" in pdf_bytes[-1024:], "Must terminate with standard PDF EOF marker"


def test_multipage_long_notes_and_page_numbers():
    """Validates that long notes spanning across multiple pages calculate dynamic Page X of Y."""
    title = "Distributed Systems Deep Dive"
    subject = "Computer Science"
    
    # Generate content that exceeds 1 page
    paragraphs = []
    for i in range(1, 35):
        paragraphs.append(
            f"### Section {i}: Consensus Protocol Step {i}\n"
            f"In distributed consensus, leader election guarantees consistent state replication across partitioned clusters. "
            f"Nodes exchange heartbeat RPCs and commit indices according to majority quorum requirements.\n"
        )
    content = "\n".join(paragraphs)

    pdf_bytes = PDFService.generate_notes_pdf(title=title, subject=subject, content=content)

    assert len(pdf_bytes) > 3000
    assert pdf_bytes.startswith(b"%PDF")

    # Read with pymupdf to inspect pages
    import fitz
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    assert doc.page_count >= 2, f"Expected at least 2 pages for long content, got {doc.page_count}"

    # Verify that each page contains the dynamic "Page X of Y" footer
    total_pages = doc.page_count
    for page_idx in range(total_pages):
        page_text = doc[page_idx].get_text()
        expected_page_str = f"Page {page_idx + 1} of {total_pages}"
        assert expected_page_str in page_text, f"Footer missing '{expected_page_str}' on page {page_idx + 1}"


def test_headings_and_lists():
    """Validates preservation of H1, H2, H3, H4, bullet lists, and numbered lists."""
    content = """# Heading 1: Foundations
## Heading 2: Mechanics
### Heading 3: Components
#### Heading 4: Deep Details

Bullet list:
- Primary bullet item one
- Primary bullet item two
* Asterisk bullet item three

Numbered list:
1. First procedural step
2. Second procedural step
3. Third procedural step
"""
    pdf_bytes = PDFService.generate_notes_pdf(title="Heading Test", subject="Testing", content=content)
    assert len(pdf_bytes) > 1000

    import fitz
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text = doc[0].get_text()
    assert "Heading 1: Foundations" in text
    assert "Heading 2: Mechanics" in text
    assert "Heading 3: Components" in text
    assert "Primary bullet item one" in text
    assert "First procedural step" in text


def test_table_rendering():
    """Validates markdown table conversion with headers, rows, and cell wrapping."""
    content = """# Hardware Specifications
| Accelerator | Architecture | Memory (VRAM) | Peak FP16 |
|---|---|---|---|
| NVIDIA H100 | Hopper | 80 GB HBM3 | 1979 TFLOPS |
| NVIDIA A100 | Ampere | 80 GB HBM2e | 624 TFLOPS |
| NVIDIA L40S | Ada Lovelace | 48 GB GDDR6 | 733 TFLOPS |
"""
    pdf_bytes = PDFService.generate_notes_pdf(title="Table Test", subject="Computer Science", content=content)
    assert len(pdf_bytes) > 1000

    import fitz
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text = doc[0].get_text()
    assert "NVIDIA H100" in text
    assert "Hopper" in text
    assert "80 GB HBM3" in text


def test_code_block_rendering():
    """Validates code block parsing and rendering inside styled containers."""
    content = """# Code Snippet Test
```python
def fibonacci(n: int) -> int:
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)
```
"""
    pdf_bytes = PDFService.generate_notes_pdf(title="Code Block Test", subject="Computer Science", content=content)
    assert len(pdf_bytes) > 1000

    import fitz
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text = doc[0].get_text()
    assert "def fibonacci(n: int)" in text
    assert "return fibonacci(n - 1)" in text


def test_math_and_callout_rendering():
    """Validates blockquotes (> callout) and inline math notation."""
    content = """# Math & Callout Test
> The amortized time complexity of dynamic array resizing is $O(1)$ despite individual reallocations taking $O(N)$ time.

The asymptotic bound is governed by:
$T(n) = 2T(n/2) + O(n)$
"""
    pdf_bytes = PDFService.generate_notes_pdf(title="Math Test", subject="Algorithms", content=content)
    assert len(pdf_bytes) > 1000

    import fitz
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text = doc[0].get_text()
    assert "Key Takeaway:" in text
    assert "amortized time complexity" in text
    assert "O(1)" in text


def test_unicode_text_handling():
    """Validates that common Unicode symbols (arrows, em-dashes, comparison operators) don't crash."""
    content = """# Unicode Test
- Complexity: $O(1) <= O(log N) <= O(N)$
- Arrows: A -> B <-> C => Done
- Punctuation: Em—dash, quotes “hello” and ‘world’, bullet • point
- Mathematical symbols: approx ~= 3.14, tolerance +/- 0.05, factor x2
"""
    pdf_bytes = PDFService.generate_notes_pdf(title="Unicode Test", subject="Testing", content=content)
    assert len(pdf_bytes) > 1000

    import fitz
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    assert doc.page_count >= 1
    text = doc[0].get_text()
    assert "Unicode Test" in text

