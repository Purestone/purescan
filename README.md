# PureScan 📄✨

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python: 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)

**PureScan** is a fast, lossless, mathematical watermark inversion tool designed specifically for scanned PDFs and multi-page document collections.

Unlike traditional AI inpainting (which hallucinates or blurs out underlying text) or naive binarization (which corrupts images and thickens strokes), **PureScan mathematically calculates the exact original pixels** using the *white-paper invariant* and inverse blend equations.

---

[English](#features) | [中文说明](#中文说明)

---

## Features

- 🎯 **100% Stroke Preservation (Zero Hallucination)**: Solves the inverse blend equation rather than painting over pixels. Formulas, dashed table lines, fine font serifs, and colored book covers are restored with sub-pixel fidelity.
- ⚡ **Blazing Fast (CPU-Friendly)**: Vectorized NumPy math processes 150+ pages in ~30 seconds on a standard laptop CPU. No GPU required.
- 📦 **Lossless PDF Stream Hot-Swapping**: Directly updates internal PDF XRef image streams in-place via PyMuPDF. Preserves PDF bookmarks, document structure, and original image resolution without re-encoding bloat.
- 🤖 **Fully Automated**: Automatically detects repeated watermark regions across pages, calculates the pristine watermark template, and inverts it with zero manual parameter tuning.

---

## Applicable Scenarios

PureScan delivers near-perfect results when the following conditions are met:

1. **Multi-page Scanned PDFs**: Document collections or scanned PDFs (typically $\ge 10$ pages).
2. **Consistent Watermark Position**: The watermark appears in roughly the same location across pages (e.g., center, footer, or diagonal repeat).
3. **Information-Preserving Blending**: The watermark was applied using **Multiply ("正片叠底")** or **semi-transparent Alpha overlay** (i.e. not 100% solid black paint).
4. **Light / White Backgrounds**: Standard textbooks, exam papers, academic dissertations, and archival scans.

> **When NOT to use**:
> - ❌ 100% opaque solid blackout markers (original pixel data was permanently destroyed).
> - ❌ Dynamic watermarks with randomized positions or dynamic timestamps on every single page.
> - ❌ Single isolated images with dense, textured painting backgrounds (no white paper reference).

---

## Mathematical Principle

Most commercial publishers and document distributors apply text watermarks using the **Multiply (正片叠底)** blend mode to ensure underlying text remains legible:

$$C(x, y) = \frac{B(x, y) \times T(x, y)}{255.0}$$

Where:
- $B(x, y)$ is the unknown original clean scan.
- $T(x, y)$ is the watermark template on white background ($T \in (0, 255]$).
- $C(x, y)$ is the observed watermarked page.

### 1. Template Extraction (The White-Paper Invariant)
Because scanned document pages contain abundant blank lines, margins, and whitespace, there exists at least one page $k$ where the underlying paper is clean white ($B_k(x, y) = 255$). At those pixels:

$$C_k(x, y) = \frac{255 \times T(x, y)}{255} = T(x, y)$$

Across independent sample pages, the pristine watermark template $T$ is recovered via a closed-form temporal maximum projection:

$$T(x, y) = \max_{k \in \text{samples}} C_k(x, y)$$

### 2. Exact Inverse Restoration
With $T$ recovered, the original image $B$ is restored deterministically:

$$B(x, y) = \min\left(255, \operatorname{round}\left(\frac{C(x, y) \times 255.0}{\max(T(x, y), 1.0)}\right)\right)$$

- On white paper: pixels saturate back to pure white ($255$).
- On black strokes: $C \approx 0 \implies B \approx 0$ (stroke thickness and darkness remain unchanged).
- On colored graphics: original RGB tones scale back to their authentic values.

---

## Installation

```bash
git clone https://github.com/Purestone/purescan.git
cd purescan
pip install -e .
```

Or install dependencies directly:
```bash
pip install -r requirements.txt
```

---

## CLI Usage

### Clean a single PDF to a new file:
```bash
purescan input.pdf -o cleaned.pdf
```

### Clean in-place (creates an automatic `.bak` backup):
```bash
purescan input.pdf --in-place
```

### Batch process an entire directory:
```bash
purescan ./scanned_books/ -o ./cleaned_books/
```

### Options:
- `-o, --output`: Destination path or output directory.
- `-i, --in-place`: Modify file in-place and save a `.bak` backup.
- `-s, --sample-pages`: Number of sample pages for template detection (default: 25).
- `-q, --quiet`: Suppress progress bar.
- `-V, --version`: Show version number.

---

## Python API

```python
from purescan import clean_pdf

result = clean_pdf(
    input_path="exam_paper.pdf",
    output_path="exam_paper_cleaned.pdf",
    sample_count=25,
)

print(f"Cleaned {result['pages_cleaned']}/{result['pages_total']} pages!")
```

---

## Comparison

| Dimension | AI Inpainting (LaMa / SD) | Color Thresholding | **PureScan** |
| :--- | :--- | :--- | :--- |
| **Formula & Stroke Integrity** | High risk of hallucination / blurring | Corrodes edges, thickens text | **100% Bit-accurate restoration** |
| **Speed (150-page PDF)** | Minutes to tens of minutes (GPU) | ~1-2 minutes | **~30-40 seconds (CPU)** |
| **Color Backgrounds** | Blurry patches | Destroys non-white colors | **Original colors preserved** |
| **PDF File Size** | Often bloats $5\times \sim 10\times$ | Re-compressed | **Lossless, size often decreases** |

---

<a name="中文说明"></a>

## 中文说明

**PureScan** 是一款专为**扫描版 PDF、教辅教材、试卷档案**设计的无损多页水印数学逆解工具。

### 为什么选择 PureScan？
市面上绝大多数去水印软件采用“AI 消除涂抹”或“二值化阈值”，遇到水印盖在文字、公式、分栏虚线上时，会造成字迹模糊、断笔或错误脑补。

PureScan 针对扫描件利用**“白纸先验”**和**正片叠底数学逆运算**，不需要 GPU，160 多页文档仅需 30 余秒即可纯 CPU 完成清理。同时直接利用 PyMuPDF 对 PDF 内部的底层图像流（XRef Stream）进行原地替换，完全保留文档目录结构、清晰度与矢量排版。

### 基本命令：
```bash
# 另存为新文件
purescan 输入.pdf -o 输出.pdf

# 原地修改（自动保留 .bak 备份）
purescan 输入.pdf --in-place

# 批量处理文件夹
purescan ./输入文件夹/ -o ./输出文件夹/
```

---

## License

Released under the [MIT License](LICENSE).
