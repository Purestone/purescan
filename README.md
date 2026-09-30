# PureScan

A lightweight tool to remove consistent watermarks from multi-page scanned PDFs.

## When to Use

PureScan works when:
- The input is a **multi-page scanned PDF** ($\ge 10$ pages).
- The watermark appears in roughly the **same location** across pages (e.g. center, footer, or diagonal repeat).
- The watermark is **semi-transparent or blended (Multiply)**, meaning the underlying text or line art is still visible underneath.
- Pages mostly consist of **white or light backgrounds** (textbooks, exams, dissertations, archives).

### When NOT to Use
- Solid, opaque blackout marks where pixel data is completely lost.
- Dynamic watermarks whose position, angle, or text content changes randomly on every page.
- Single-page isolated images with textured or complex backgrounds.
- Pure vector PDFs (vector watermarks can be removed by deleting PDF content objects directly).

---

## Installation

```bash
git clone https://github.com/Purestone/purescan.git
cd purescan
pip install -e .
```

Or install dependencies with:
```bash
pip install -r requirements.txt
```

---

## Usage

### Command Line

```bash
# Save output to a new file
purescan input.pdf -o output.pdf

# Overwrite in place (automatically creates an input.pdf.bak backup)
purescan input.pdf --in-place

# Batch process a directory
purescan ./input_dir/ -o ./output_dir/
```

#### Options:
- `-o, --output`: Output file or directory path.
- `-i, --in-place`: Modify file in-place and create a `.bak` backup.
- `-s, --sample-pages`: Number of sample pages to use for template detection (default: `25`).
- `-q, --quiet`: Disable progress output.
- `-V, --version`: Show version.

---

### Python API

```python
from purescan import clean_pdf

result = clean_pdf(
    input_path="document.pdf",
    output_path="document_cleaned.pdf",
    sample_count=25,
)

print(f"Processed: {result['pages_cleaned']}/{result['pages_total']} pages")
```

---

## License

MIT
