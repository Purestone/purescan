"""Unit tests for PureScan mathematical core."""

import numpy as np
import unittest

from purescan.core import extract_template, invert_multiply, detect_watermark_bbox


def test_extract_template_and_invert_multiply():
    # Synthetic ground truth background (2 pages: one has text, one is blank white)
    h, w = 40, 100
    bg_page1 = np.full((h, w, 3), 255, dtype=np.uint8)
    bg_page1[10:30, 20:80] = 0  # Black text box

    bg_page2 = np.full((h, w, 3), 255, dtype=np.uint8)  # Clean white paper

    # Watermark template: gray text stamped on pure white paper
    # E.g. watermark text is gray 150, background is 255
    true_template = np.full((h, w, 3), 255, dtype=np.uint8)
    true_template[15:25, 30:70] = 150  # Watermark text

    # Apply Multiply blend: C = (B * T) / 255
    c_page1 = np.clip(np.round(bg_page1.astype(float) * true_template.astype(float) / 255.0), 0, 255).astype(np.uint8)
    c_page2 = np.clip(np.round(bg_page2.astype(float) * true_template.astype(float) / 255.0), 0, 255).astype(np.uint8)

    crops = np.stack([c_page1, c_page2], axis=0)

    # 1. Test template extraction via np.max
    recovered_template = extract_template(crops)
    # The recovered template should match true_template exactly!
    np.testing.assert_allclose(recovered_template, true_template, atol=1.0)

    # 2. Test mathematical inversion on page 1 (where watermark overlapped black text and white space)
    restored_page1 = invert_multiply(c_page1, recovered_template)

    # Under pure black text (0), restored should still be 0!
    assert np.all(restored_page1[15:25, 30:70][bg_page1[15:25, 30:70] == 0] == 0)

    # On white background, restored should be 255!
    assert np.all(restored_page1[15:25, 30:70][bg_page1[15:25, 30:70] == 255] == 255)

    # Overall restored page1 should perfectly match original bg_page1
    np.testing.assert_allclose(restored_page1, bg_page1, atol=1.0)


def test_detect_watermark_bbox():
    h, w = 100, 200
    crops = []
    for _ in range(5):
        crop = np.full((h, w, 3), 245, dtype=np.uint8)
        # Add colored tint watermark at y: [40, 60], x: [50, 150]
        crop[40:60, 50:150, 0] = 100  # R
        crop[40:60, 50:150, 1] = 120  # G
        crop[40:60, 50:150, 2] = 180  # B (blue tint)
        crops.append(crop)

    stacked = np.stack(crops, axis=0)
    bbox = detect_watermark_bbox(stacked)
    assert bbox is not None
    r_min, r_max, c_min, c_max = bbox
    assert r_min <= 40
    assert r_max >= 60
    assert c_min <= 50
    assert c_max >= 150
