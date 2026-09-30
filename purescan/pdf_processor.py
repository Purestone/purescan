"""PDF document processor for lossless stream-level watermark inversion."""

from pathlib import Path
import shutil
import tempfile
from typing import Any, Callable, Dict, List, Optional
import fitz
import numpy as np

from .core import detect_watermark_bbox, extract_template, invert_multiply


def clean_pdf(
    input_path: Path | str,
    output_path: Optional[Path | str] = None,
    *,
    in_place: bool = False,
    sample_count: int = 20,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> Dict[str, Any]:
    """Clean repeated raster watermarks from a multi-page scanned PDF.

    Args:
        input_path: Path to the input PDF file.
        output_path: Destination path for cleaned PDF. Required if in_place is False.
        in_place: If True, overwrites input_path in-place and saves a .bak backup.
        sample_count: Number of sample pages to use for template estimation.
        progress_callback: Optional callback fn(current_page, total_pages).

    Returns:
        Dictionary with processing statistics.
    """
    src = Path(input_path).resolve()
    if not src.exists():
        raise FileNotFoundError(f"Input file not found: {src}")

    if in_place:
        dest = src
    elif output_path is not None:
        dest = Path(output_path).resolve()
    else:
        raise ValueError("Must provide either output_path or set in_place=True")

    doc = fitz.open(src)
    total_pages = len(doc)
    if total_pages == 0:
        doc.close()
        raise ValueError("PDF document has 0 pages.")

    # 1. Determine dominant image resolution across pages
    resolutions: Dict[tuple[int, int], int] = {}
    step = max(1, total_pages // sample_count)
    sample_indices = list(range(0, total_pages, step))[:sample_count]

    for idx in sample_indices:
        imgs = doc[idx].get_images()
        if imgs:
            h, w = imgs[0][3], imgs[0][2]
            resolutions[(h, w)] = resolutions.get((h, w), 0) + 1

    if not resolutions:
        doc.close()
        raise RuntimeError("No raster images found in PDF.")

    target_h, target_w = max(resolutions.items(), key=lambda x: x[1])[0]

    # 2. Extract crops in the typical central vertical band (35% to 75% height)
    y_start, y_end = int(0.35 * target_h), int(0.75 * target_h)
    crops: List[np.ndarray] = []

    for idx in sample_indices:
        imgs = doc[idx].get_images()
        if not imgs or imgs[0][3] != target_h or imgs[0][2] != target_w:
            continue
        try:
            stream = doc.xref_stream(imgs[0][0])
            if len(stream) != target_h * target_w * 3:
                continue
            arr = np.frombuffer(stream, dtype=np.uint8).reshape(target_h, target_w, 3)
            crops.append(arr[y_start:y_end, :, :3])
        except Exception:
            continue

    if len(crops) < 2:
        doc.close()
        raise RuntimeError("Insufficient compatible page images to detect watermark.")

    stacked_crops = np.stack(crops, axis=0)

    # 3. Detect bounding box of the watermark
    bbox = detect_watermark_bbox(stacked_crops)
    if bbox is None:
        doc.close()
        return {
            "success": False,
            "message": "No consistent repeated watermark detected across pages.",
            "pages_total": total_pages,
            "pages_cleaned": 0,
        }

    r_min, r_max, c_min, c_max = bbox
    y1, y2 = y_start + r_min, y_start + r_max
    x1, x2 = c_min, c_max

    # 4. Extract pristine template using maximum projection
    tmpl_step = max(1, total_pages // max(sample_count, 25))
    tmpl_indices = list(range(0, total_pages, tmpl_step))
    tmpl_crops: List[np.ndarray] = []

    for idx in tmpl_indices:
        imgs = doc[idx].get_images()
        if not imgs or imgs[0][3] != target_h or imgs[0][2] != target_w:
            continue
        try:
            stream = doc.xref_stream(imgs[0][0])
            if len(stream) != target_h * target_w * 3:
                continue
            arr = np.frombuffer(stream, dtype=np.uint8).reshape(target_h, target_w, 3)
            tmpl_crops.append(arr[y1:y2, x1:x2, :3])
        except Exception:
            continue

    if not tmpl_crops:
        doc.close()
        raise RuntimeError("Failed to extract template crops.")

    template = extract_template(np.stack(tmpl_crops, axis=0))
    wm_mask = np.any(template < 252, axis=2)

    if np.sum(wm_mask) < 20:
        doc.close()
        return {
            "success": False,
            "message": "Detected watermark pattern is too small or negligible.",
            "pages_total": total_pages,
            "pages_cleaned": 0,
        }

    # 5. Invert and update image streams across all pages
    cleaned_count = 0
    for p in range(total_pages):
        page = doc[p]
        imgs = page.get_images()
        if not imgs or imgs[0][3] != target_h or imgs[0][2] != target_w:
            if progress_callback:
                progress_callback(p + 1, total_pages)
            continue

        xref = imgs[0][0]
        stream = doc.xref_stream(xref)
        if len(stream) != target_h * target_w * 3:
            if progress_callback:
                progress_callback(p + 1, total_pages)
            continue

        arr = np.frombuffer(stream, dtype=np.uint8).reshape(target_h, target_w, 3).copy()
        crop = arr[y1:y2, x1:x2, :3]
        arr[y1:y2, x1:x2, :3] = invert_multiply(crop, template, mask=wm_mask)

        doc.update_stream(xref, arr.tobytes(), compress=True)
        cleaned_count += 1

        if progress_callback:
            progress_callback(p + 1, total_pages)

    # 6. Save output atomically
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        doc.save(tmp_path, deflate=True)
        doc.close()

        if in_place and dest.exists():
            backup_path = dest.with_name(f"{dest.name}.bak")
            shutil.copy2(dest, backup_path)

        shutil.move(tmp_path, dest)
    except Exception as e:
        doc.close()
        tmp_path.unlink(missing_ok=True)
        raise RuntimeError(f"Failed to save cleaned PDF: {e}") from e

    return {
        "success": True,
        "pages_total": total_pages,
        "pages_cleaned": cleaned_count,
        "bbox": (y1, y2, x1, x2),
        "output_path": str(dest),
    }
