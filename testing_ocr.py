from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path

import cv2
import numpy as np
import pytesseract


EXPECTED_TASKS = 10


@dataclass
class TaskRow:
    text: str
    y_norm: float
    crop: np.ndarray


def detect_row_centers(image: np.ndarray) -> list[float]:
    """
    Detect completed task rows by finding the green completion checkmarks.

    Returns a list of Y coordinates, one for each visible completed task row.
    """
    h, w = image.shape[:2]

    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    # Green completion checkmarks.
    green_mask = cv2.inRange(
        hsv,
        np.array([35, 75, 45], dtype=np.uint8),
        np.array([95, 255, 255], dtype=np.uint8),
    )

    # The completion checkmarks live in this horizontal region.
    x0 = int(0.53 * w)
    x1 = int(0.62 * w)

    y0 = int(0.15 * h)
    y1 = int(0.92 * h)

    roi_mask = np.zeros_like(green_mask)
    roi_mask[y0:y1, x0:x1] = 255

    green_mask = cv2.bitwise_and(green_mask, roi_mask)

    count, labels, stats, centroids = cv2.connectedComponentsWithStats(
        green_mask
    )

    centers = []

    for i in range(1, count):
        x, y, width, height, area = stats[i]

        # Filter out random green UI elements/noise.
        if area < max(500, int(0.00035 * w * h)):
            continue

        if not (0.012 * w <= width <= 0.04 * w):
            continue

        if not (0.025 * h <= height <= 0.075 * h):
            continue

        centers.append(y + height / 2)

    centers.sort()

    # Collapse anything accidentally detected twice.
    deduplicated = []

    for y in centers:
        if not deduplicated:
            deduplicated.append(y)

        elif y - deduplicated[-1] > 0.05 * h:
            deduplicated.append(y)

        else:
            deduplicated[-1] = (deduplicated[-1] + y) / 2

    return deduplicated


def clean_ocr(text: str) -> str:
    """
    Clean common Tesseract junk without being too aggressive.

    It is better to preserve slightly ugly OCR than accidentally remove
    information from a task.
    """
    text = text.replace("|", " ")
    text = text.replace("\\", " ")

    text = re.sub(r"\s+", " ", text).strip()

    return text.strip(" -,:;")


def ocr_row(
    image: np.ndarray,
    center_y: float,
) -> tuple[str, np.ndarray]:
    """
    OCR one task row.

    We deliberately exclude the 320-point value and green checkmark because
    they add OCR noise and are not part of the task description.
    """
    h, w = image.shape[:2]

    y1 = max(0, int(center_y - 0.050 * h))
    y2 = min(h, int(center_y + 0.050 * h))

    x1 = int(0.235 * w)
    x2 = int(0.50 * w)

    crop = image[y1:y2, x1:x2]

    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)

    # Upscaling significantly improves Tesseract on Hay Day text.
    gray = cv2.resize(
        gray,
        None,
        fx=2.2,
        fy=2.2,
        interpolation=cv2.INTER_CUBIC,
    )

    # Brown text is substantially darker than the row background.
    _, binary = cv2.threshold(
        gray,
        190,
        255,
        cv2.THRESH_BINARY,
    )

    text = pytesseract.image_to_string(
        binary,
        config="--psm 6",
    )

    text = clean_ocr(text)

    return text, crop


def read_screenshot(path: Path) -> list[TaskRow]:
    """
    Locate and OCR all visible completed derby tasks in one screenshot.
    """
    image = cv2.imread(str(path))

    if image is None:
        raise ValueError(
            f"Could not read image: {path}"
        )

    h, w = image.shape[:2]

    centers = detect_row_centers(image)

    rows = []

    for center_y in centers:
        text, crop = ocr_row(
            image,
            center_y,
        )

        rows.append(
            TaskRow(
                text=text,
                y_norm=center_y / h,
                crop=crop,
            )
        )

    return rows


def normalize_task_text(text: str) -> str:
    """
    Normalize OCR output for fuzzy comparisons.
    """
    text = text.lower()

    # Common OCR confusion in "lbs".
    text = text.replace("ibs", "lbs")

    text = re.sub(
        r"[^a-z0-9]+",
        " ",
        text,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def task_similarity(
    first: TaskRow,
    second: TaskRow,
) -> float:
    """
    Fuzzy similarity between two OCR'd task rows.
    """
    a = normalize_task_text(first.text)
    b = normalize_task_text(second.text)

    if not a or not b:
        return 0.0

    return SequenceMatcher(
        None,
        a,
        b,
    ).ratio()


def overlap_score(
    first: list[TaskRow],
    second: list[TaskRow],
    overlap: int,
) -> float:
    """
    Test the hypothesis:

        end of FIRST == beginning of SECOND
    """
    if overlap <= 0:
        return 0.0

    scores = []

    for a, b in zip(
        first[-overlap:],
        second[:overlap],
    ):
        scores.append(
            task_similarity(a, b)
        )

    return sum(scores) / len(scores)


def screenshot_looks_like_top(
    rows: list[TaskRow],
) -> bool:
    """
    At the top of the derby log, the 'Personal Derby Task Log' heading occupies
    vertical space before the first task.

    Therefore the first visible completed task sits substantially lower.

    This matters specifically when the two screenshots have ZERO overlap.
    """
    if not rows:
        return False

    return rows[0].y_norm > 0.34


def merge_rows(
    first: list[TaskRow],
    second: list[TaskRow],
    expected_tasks: int = EXPECTED_TASKS,
) -> tuple[list[TaskRow], dict]:
    """
    Reconstruct the complete ordered task log from two screenshots.

    Key observation:

        visible rows A
      + visible rows B
      - 10 total derby tasks
      = number of duplicated/overlapping rows

    This means we don't need to guess how much the screenshots overlap.
    """

    total_visible = len(first) + len(second)

    overlap = total_visible - expected_tasks

    if overlap < 0:
        raise ValueError(
            f"Only found {total_visible} completed task rows across both "
            f"screenshots, but {expected_tasks} are required."
        )

    if overlap > min(
        len(first),
        len(second),
    ):
        raise ValueError(
            "The detected row counts imply an impossible screenshot overlap.\n"
            f"Screenshot A: {len(first)} rows\n"
            f"Screenshot B: {len(second)} rows\n"
            f"Implied overlap: {overlap}"
        )

    #
    # NO OVERLAP
    #
    # Example 3:
    #
    #     screenshot A = 4 tasks
    #     screenshot B = 6 tasks
    #
    # Exactly ten visible rows means we simply need to determine which
    # screenshot came first.
    #
    if overlap == 0:
        first_is_top = screenshot_looks_like_top(
            first
        )

        second_is_top = screenshot_looks_like_top(
            second
        )

        if first_is_top and not second_is_top:
            return (
                first + second,
                {
                    "overlap": 0,
                    "order": "A then B",
                    "confidence": 1.0,
                },
            )

        if second_is_top and not first_is_top:
            return (
                second + first,
                {
                    "overlap": 0,
                    "order": "B then A",
                    "confidence": 1.0,
                },
            )

        raise ValueError(
            "The screenshots contain exactly 10 task rows and therefore "
            "have no overlap, but I cannot reliably determine which screenshot "
            "contains the beginning of the task log.\n\n"
            "For zero-overlap screenshots, make sure the "
            "'Personal Derby Task Log' heading is visible in the first screenshot."
        )

    #
    # WITH OVERLAP
    #
    # There are only two possibilities:
    #
    #     end of A == beginning of B
    #
    # or
    #
    #     end of B == beginning of A
    #

    score_a_then_b = overlap_score(
        first,
        second,
        overlap,
    )

    score_b_then_a = overlap_score(
        second,
        first,
        overlap,
    )

    best_score = max(
        score_a_then_b,
        score_b_then_a,
    )

    if best_score < 0.48:
        raise ValueError(
            f"The row counts say there should be {overlap} overlapping "
            f"task row(s), but the OCR could not verify the overlap.\n\n"
            f"A -> B similarity: {score_a_then_b:.2f}\n"
            f"B -> A similarity: {score_b_then_a:.2f}"
        )

    #
    # A -> B
    #
    if score_a_then_b >= score_b_then_a:
        merged = (
            first
            + second[overlap:]
        )

        return (
            merged,
            {
                "overlap": overlap,
                "order": "A then B",
                "confidence": score_a_then_b,
            },
        )

    #
    # B -> A
    #
    merged = (
        second
        + first[overlap:]
    )

    return (
        merged,
        {
            "overlap": overlap,
            "order": "B then A",
            "confidence": score_b_then_a,
        },
    )


def analyze_derby(
    first_image: Path,
    second_image: Path,
) -> dict:
    """
    Public function if you eventually want to call this from Greg instead
    of from the command line.
    """
    first_rows = read_screenshot(
        first_image
    )

    second_rows = read_screenshot(
        second_image
    )

    merged_rows, metadata = merge_rows(
        first_rows,
        second_rows,
    )

    if len(merged_rows) != EXPECTED_TASKS:
        raise ValueError(
            f"Expected {EXPECTED_TASKS} final tasks, "
            f"but reconstructed {len(merged_rows)}."
        )

    return {
        "tasks": [
            row.text
            for row in merged_rows
        ],

        "metadata": {
            **metadata,

            "rows_detected_in_a":
                len(first_rows),

            "rows_detected_in_b":
                len(second_rows),
        },
    }


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Recover a Hay Day player's 10 completed derby tasks "
            "from two screenshots of their Personal Derby Task Log."
        )
    )

    parser.add_argument(
        "image_a",
        type=Path,
        help="First screenshot",
    )

    parser.add_argument(
        "image_b",
        type=Path,
        help="Second screenshot",
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output machine-readable JSON",
    )

    args = parser.parse_args()

    try:
        result = analyze_derby(
            args.image_a,
            args.image_b,
        )

    except Exception as error:
        print(
            f"ERROR: {error}"
        )

        raise SystemExit(1)

    if args.json:
        print(
            json.dumps(
                result,
                indent=2,
            )
        )

        return

    metadata = result["metadata"]

    print(
        f"Screenshot A rows: "
        f"{metadata['rows_detected_in_a']}"
    )

    print(
        f"Screenshot B rows: "
        f"{metadata['rows_detected_in_b']}"
    )

    print(
        f"Order: "
        f"{metadata['order']}"
    )

    print(
        f"Overlap: "
        f"{metadata['overlap']} row(s)"
    )

    print(
        f"Overlap confidence: "
        f"{metadata['confidence']:.2f}"
    )

    print()

    for number, task in enumerate(
        result["tasks"],
        start=1,
    ):
        print(
            f"{number:2}. {task}"
        )


if __name__ == "__main__":
    main()