#!/usr/bin/env python3
"""Offline OCR of English Hay Day derby logs. Requires Tesseract 5, Pillow, NumPy.

    python derby_ocr.py top.jpg bottom.jpg --json result.json

The CLI returns 0 for a resolved log, 2 for a log needing review, and 1 for an
input/dependency error. An expected count is a validation constraint, never a
license to insert or delete tasks. See README.md for assumptions and limitations.

Writen by ChatGPT 6
"""
from __future__ import annotations

import argparse
import csv
import io
import itertools
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from dataclasses import dataclass, field
from difflib import SequenceMatcher, get_close_matches
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

VERSION = "1.2.0"


@dataclass
class OCR:
    text: str
    confidence: float
    words: list[dict] = field(default_factory=list)
    raw_text: str | None = None
    quantity_check: dict | None = None


@dataclass
class Task:
    category: str
    quantity: int | None
    item: str
    text: str
    components: list[dict] = field(default_factory=list)


@dataclass
class Row:
    crop: Image.Image
    center: float
    marker_height: float
    status: str
    source: dict
    readings: list[OCR] = field(default_factory=list)
    task: Task | None = None
    clipped_top: bool = False
    clipped_bottom: bool = False
    body: Image.Image | None = None
    basket_reading: OCR | None = None
    resolution_warnings: list[str] = field(default_factory=list)

    @property
    def best(self) -> OCR:
        return max(self.readings, key=reading_score)


@dataclass
class Page:
    source: str
    rows: list[Row]
    has_header: bool
    warnings: list[str]


class Engine:
    def __init__(self, executable: str = "tesseract", timeout: float = 20):
        self.executable = shutil.which(executable)
        if not self.executable:
            raise ValueError("Tesseract was not found. Install Tesseract with English data; "
                             "use --tesseract PATH if it is not on PATH.")
        self.timeout = timeout

    def read(self, image: Image.Image, psm: int = 6, whitelist: str | None = None) -> OCR:
        with tempfile.TemporaryDirectory(prefix="derby_ocr_") as directory:
            path = Path(directory) / "crop.png"
            ImageOps.expand(image, border=16, fill="white").save(path)
            # argv, not a shell; filenames and executable paths are never evaluated.
            command = [self.executable, str(path), "stdout", "-l", "eng", "--psm", str(psm)]
            if whitelist is not None:
                command.extend(["-c", f"tessedit_char_whitelist={whitelist}"])
            result = subprocess.run(
                [*command, "tsv"],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=self.timeout, env={**os.environ, "OMP_THREAD_LIMIT": "1"},
            )
            if result.returncode:
                raise ValueError(f"Tesseract failed: {result.stderr.strip()}")
        lines: dict[tuple, list[str]] = {}
        scores = []
        words = []
        for word in csv.DictReader(io.StringIO(result.stdout), delimiter="\t", quoting=csv.QUOTE_NONE):
            token = (word.get("text") or "").strip()
            confidence = float(word.get("conf", -1))
            if not token or confidence < 0:
                continue
            left = int(word["left"]) - 16
            right = left + int(word["width"])
            # The neighboring points star can leave a narrow stroke at the
            # crop boundary, confidently misread as "i" or "l". Keep the
            # multiplication "x" and all interior/name words untouched.
            if token.lower() in {"i", "l"} and (left < image.width * .02 or right > image.width * .98):
                continue
            key = tuple(word[k] for k in ("block_num", "par_num", "line_num"))
            lines.setdefault(key, []).append(token)
            words.append({"text": token, "left": left, "top": int(word["top"]) - 16,
                          "width": int(word["width"]), "height": int(word["height"]),
                          "confidence": confidence})
            length = sum(c.isalnum() for c in token)
            if length:
                scores.append((confidence, length))
        confidence = sum(c * n for c, n in scores) / max(1, sum(n for _, n in scores))
        return OCR("\n".join(" ".join(line) for line in lines.values()), round(confidence, 2), words)


def bands(mask: np.ndarray) -> list[tuple[int, int]]:
    indices = np.flatnonzero(mask)
    if not len(indices):
        return []
    groups = np.split(indices, np.where(np.diff(indices) > 1)[0] + 1)
    return [(int(g[0]), int(g[-1] + 1)) for g in groups]


def find_panel(image: Image.Image) -> tuple[int, int, int, int]:
    """Find the largest pale-yellow connected region, independently of resolution."""
    small = image.copy()
    small.thumbnail((500, 500))
    a = np.asarray(small, dtype=float)
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    mask = (r > 180) & (g > 170) & (abs(r - g) < 48) & (b < g * .91) & (b > g * .40)
    seen = np.zeros(mask.shape, dtype=bool)
    best: list[tuple[int, int]] = []
    height, width = mask.shape
    for y, x in zip(*np.nonzero(mask)):
        if seen[y, x]:
            continue
        queue = [(y, x)]
        seen[y, x] = True
        component = []
        while queue:
            v, u = queue.pop()
            component.append((v, u))
            for yy, xx in ((v - 1, u), (v + 1, u), (v, u - 1), (v, u + 1)):
                if 0 <= yy < height and 0 <= xx < width and mask[yy, xx] and not seen[yy, xx]:
                    seen[yy, xx] = True
                    queue.append((yy, xx))
        if len(component) > len(best):
            best = component
    if len(best) < width * height * .025:
        raise ValueError("Could not locate the pale-yellow task log. Use an unobstructed landscape screenshot.")
    yy, xx = np.array(best).T
    sx, sy = image.width / width, image.height / height
    box = tuple(round(v) for v in (xx.min() * sx, yy.min() * sy, (xx.max() + 1) * sx, (yy.max() + 1) * sy))
    if box[2] - box[0] < image.width * .15 or box[3] - box[1] < image.height * .25:
        raise ValueError("The detected yellow region is too small to be a task log.")
    return box


def clean(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).lower().replace("×", "x")
    text = re.sub(r"[^a-z0-9&<>£\s]", " ", text)
    text = " ".join(text.split())
    tokens = text.split()
    actions = ["produce", "harvest", "fully", "help", "feed", "collect", "catch", "serve", "complete", "mine"]
    if tokens and tokens[0] not in actions:
        match = get_close_matches(tokens[0], actions, n=1, cutoff=.75)
        if match:
            tokens[0] = match[0]
    if tokens and tokens[0] == "produce":
        for i in range(1, min(4, len(tokens))):
            if SequenceMatcher(None, tokens[i], "collect").ratio() >= .72:
                tokens[i] = "collect"
    return " ".join(tokens)


def parse_task(text: str) -> Task | None:
    """Parse task grammar; product/crop/building names come from OCR, not a fixture list."""
    s = clean(text)
    m = re.match(r"produce\b.*?\bcollect\s+([<£]?[0-9oilsz]+)\s*[xk]\s*([a-z].*)", s)
    if m:
        number, item = m.groups()
        quantity = None if number[0] in "<£" else int(number.translate(str.maketrans("oilsz", "01152")))
        return Task("production", quantity, item, f"Produce & collect {quantity if quantity is not None else '?'} x {item}")
    m = re.match(r"harvest\s+(\d+)\s+(.+?)\s+fields?$", s)
    if m:
        n, item = m.groups()
        return Task("harvest", int(n), item, f"Harvest {n} {item} fields")
    m = re.match(r"collect\s+(\d+)\s+([a-z].*)", s)
    if m:
        n, item = m.groups()
        return Task("collect", int(n), item, f"Collect {n} {item}")
    m = re.match(r"fully serve\s+(\d+)\s+(.+?)\s+in your\s+\w+$", s)
    if m:
        n, item = m.groups()
        return Task("town", int(n), item, f"Fully serve {n} {item} in your town")
    m = re.fullmatch(r"fully serve\s+(\d+)\s+x\s+([a-z][a-z ]*)", s)
    if m:
        n, item = m.groups()
        return Task("town_visitor", int(n), item, f"Fully serve {n} x {item}")
    m = re.match(r"serve\s+(\d+)\s+town visitors in\s+(.+)$", s)
    if m:
        n, item = m.groups()
        return Task("town_building", int(n), item, f"Serve {n} town visitors in {item}")
    m = re.match(r"help\b.*?farmers\s+(\d+)\s+\w+$", s)
    if m:
        n = int(m[1])
        return Task("help", n, "farmers", f"Help other farmers {n} times")
    m = re.match(r"feed\s+(\d+)\s+anima[l1i]s$", s)
    if m:
        n = int(m[1])
        return Task("feed", n, "animals", f"Feed {n} animals")
    m = re.match(r"catch\s+(\d+)\s+[li1]bs\s+of fish with lures$", s)
    if m:
        n = int(m[1])
        return Task("fishing", n, "fish", f"Catch {n} lbs of fish with lures")
    m = re.match(r"complete\b.*?\b(\d+)\s+boats$", s)
    if m:
        n = int(m[1])
        return Task("boats", n, "boats", f"Complete and send off {n} boats")
    m = re.match(r"complete\s+(\d+)\s+truck deliveries$", s)
    if m:
        n = int(m[1])
        return Task("trucks", n, "truck deliveries", f"Complete {n} truck deliveries")
    m = re.match(r"mine\s+(\d+)\s+ores?$", s)
    if m:
        n = int(m[1])
        return Task("mining", n, "ore", f"Mine {n} ore")
    return None


def reading_score(reading: OCR) -> float:
    task = parse_task(reading.text)
    return reading.confidence + (25 if task else 0) + (10 if task and task.quantity is not None else 0)


def brown_mask(image: Image.Image) -> np.ndarray:
    a = np.asarray(image.convert("RGB"), dtype=float)
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    return (r > g * 1.10) & (g > b * 1.05) & (r < 190) & (g < 150) & (g > 45)


def quantity_word(reading: OCR) -> int | None:
    """Locate a quantity token using task grammar, without guessing its value.

    Trying a sentinel only locates the slot. The replacement returned to the
    caller always comes from OCR of that slot's pixels, never this sentinel.
    In particular, letters in product names cannot become task quantities.
    """
    spans = list(re.finditer(r"\S+", reading.text))
    if len(spans) != len(reading.words):
        return None
    for i, span in enumerate(spans):
        if not re.fullmatch(r"[0-9oOiIlLsSzZbBgG]{1,5}", span[0]):
            continue
        probe = reading.text[:span.start()] + "1234567" + reading.text[span.end():]
        task = parse_task(probe)
        if task and task.quantity == 1234567:
            return i
    return None


def verify_quantity(engine: Engine, crop: Image.Image, readings: list[OCR]) -> None:
    """Retry uncertain quantity tokens with digits-only OCR and retain evidence."""
    candidates = [(reading, index) for reading in readings
                  if (index := quantity_word(reading)) is not None]
    if not candidates:
        return
    original = [r.words[i]["text"] for r, i in candidates]
    needs_retry = (len(set(original)) > 1 or
                   any(not text.isascii() or not text.isdigit() for text in original) or
                   any(r.words[i]["confidence"] < 80 for r, i in candidates))
    if not needs_retry:
        return
    reading, index = max(candidates, key=lambda pair: reading_score(pair[0]))
    word = reading.words[index]
    padding = max(3, round(word["height"] * .1))
    bounds = (max(0, word["left"] - padding), max(0, word["top"] - padding),
              min(crop.width, word["left"] + word["width"] + padding),
              min(crop.height, word["top"] + word["height"] + padding))
    number_crop = crop.crop(bounds)
    mask = Image.fromarray(np.where(brown_mask(number_crop), 0, 255).astype("uint8"))
    attempts = []
    for name, image, psm in [("color", number_crop, 13), ("text_mask", mask, 13)]:
        result = engine.read(image, psm=psm, whitelist="0123456789")
        attempts.append({"mode": name, "text": result.text.strip(), "confidence": result.confidence})
    reliable = [a for a in attempts if re.fullmatch(r"[0-9]{1,5}", a["text"]) and a["confidence"] >= 75]
    if len(reliable) < 2:
        for name, image in [("color_line", number_crop), ("text_mask_line", mask)]:
            result = engine.read(image, psm=7, whitelist="0123456789")
            attempts.append({"mode": name, "text": result.text.strip(), "confidence": result.confidence})
        reliable = [a for a in attempts if re.fullmatch(r"[0-9]{1,5}", a["text"]) and a["confidence"] >= 75]
    values = {int(a["text"]) for a in reliable}
    accepted = len(reliable) >= 2 and len(values) == 1
    quantity = next(iter(values)) if accepted else None
    # A consistent full-row digit reading can corroborate one weaker isolated
    # reading. This can only confirm the existing value, never change it.
    # Context helps with narrow glyphs such as the two 1s in "117".
    if not accepted and len(set(original)) == 1 and original[0].isascii() and original[0].isdigit():
        existing = int(original[0])
        supported = any(a["text"] == original[0] and a["confidence"] >= 70 for a in attempts)
        if (supported and values <= {existing} and
                max(r.words[i]["confidence"] for r, i in candidates) >= 80):
            accepted, quantity = True, existing
    check = {"status": "verified" if accepted else "needs_review", "original_tokens": original,
             "quantity": quantity,
             "bbox_in_row_crop": list(bounds), "attempts": attempts}
    for result in readings:
        result.quantity_check = check
    if not accepted:
        return
    number = str(check["quantity"])
    for result, index in candidates:
        span = list(re.finditer(r"\S+", result.text))[index]
        if span[0] != number:
            result.raw_text = result.text
            result.text = result.text[:span.start()] + number + result.text[span.end():]
            result.words = [dict(w) for w in result.words]
            result.words[index]["text"] = number
            result.words[index]["confidence"] = min((a["confidence"] for a in reliable),
                                                     default=result.words[index]["confidence"])


def read_row(engine: Engine, crop: Image.Image) -> list[OCR]:
    reading = engine.read(crop)
    readings = [reading]
    if not parse_task(reading.text) or reading.confidence < 83:
        mask = Image.fromarray(np.where(brown_mask(crop), 0, 255).astype("uint8"))
        readings.append(engine.read(mask))
    verify_quantity(engine, crop, readings)
    return readings


def icon_feature(image: Image.Image) -> np.ndarray | None:
    """Normalize a pictured icon, removing the yellow panel behind it.

    No external models or hard-coded icon labels are used. Labels are learned
    from ordinary text tasks in the same submitted log.
    """
    a = np.asarray(image.convert("RGB"), dtype=float)
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    background = (r > 175) & (g > 165) & (abs(r - g) < 60) & (b < g * .93) & (b > g * .38)
    ys, xs = np.nonzero(~background)
    if len(xs) < 25:
        return None
    a[background] = 255
    cut = Image.fromarray(a.astype("uint8")).crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
    cut.thumbnail((64, 64), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (64, 64), "white")
    canvas.paste(cut, ((64 - cut.width) // 2, (64 - cut.height) // 2))
    vector = (255 - np.asarray(canvas, dtype=float)).ravel()
    norm = float(np.linalg.norm(vector))
    return vector / norm if norm else None


def multiplier_groups(reading: OCR) -> list[dict]:
    """Read x16 or x 16 and retain its horizontal position and confidence."""
    words = sorted(reading.words, key=lambda w: w["left"])
    groups = []
    for i, word in enumerate(words):
        # A small, compressed multiplication cross is sometimes read as '*'.
        # Interpret it only in the narrow multiplier-plus-number grammar.
        token = word["text"].lower().replace("×", "x").replace("*", "x")
        match = re.fullmatch(r"x\s*([0-9oilz]+)", token)
        last = word
        if token == "x" and i + 1 < len(words):
            following = words[i + 1]
            if following["left"] - word["left"] < 100:
                match = re.fullmatch(r"([0-9oilz]+)", following["text"].lower())
                last = following
        if match:
            quantity = int(match[1].translate(str.maketrans("oilz", "0112")))
            if quantity > 0:
                groups.append({"quantity": quantity, "left": word["left"],
                               "right": last["left"] + last["width"],
                               "confidence": min(word["confidence"], last["confidence"])})
    return groups


def build_icon_bank(pages: list[Page]) -> list[dict]:
    bank = []
    for page in pages:
        for row in page.rows:
            if not row.task or row.task.category == "basket" or row.body is None:
                continue
            if row.best.confidence < 75 or row.clipped_top or row.clipped_bottom:
                continue
            feature = icon_feature(row.body.crop((30, 0, 180, row.body.height)))
            if feature is not None:
                bank.append({"category": row.task.category, "item": row.task.item,
                             "feature": feature, "source": dict(row.source)})
    return bank


def match_icon(image: Image.Image, bank: list[dict]) -> dict | None:
    feature = icon_feature(image)
    if feature is None:
        return None
    by_label = {}
    for template in bank:
        key = template["category"], template["item"]
        score = float(feature @ template["feature"])
        if key not in by_label or score > by_label[key][0]:
            by_label[key] = (score, template)
    ranked = sorted(by_label.values(), key=lambda pair: pair[0], reverse=True)
    if not ranked:
        return None
    score, template = ranked[0]
    runner_up = ranked[1][0] if len(ranked) > 1 else 0
    # Similar colors alone are insufficient: require a strong shape match and
    # separation from the next distinct label. Unknown icons remain unknown.
    if score < .80 or score - runner_up < .12:
        return None
    return {"category": template["category"], "item": template["item"],
            "icon_similarity": round(score, 4), "reference": template["source"]}


def resolve_baskets(pages: list[Page], engine: Engine) -> None:
    bank = build_icon_bank(pages)
    for page in pages:
        for row in page.rows:
            if row.task or row.body is None:
                continue
            mask = Image.fromarray(np.where(brown_mask(row.body), 0, 255).astype("uint8"))
            reading = engine.read(mask, psm=6)
            groups = multiplier_groups(reading)
            if not 2 <= len(groups) <= 4:
                continue
            evidence = [reading.text]
            if any(g["confidence"] < 75 for g in groups):
                alternate = engine.read(mask, psm=7)
                evidence.append(alternate.text)
                alternate_groups = multiplier_groups(alternate)
                for i, group in enumerate(groups):
                    nearby = [g for g in alternate_groups if abs(g["left"] - group["left"]) < 20]
                    if any(g["quantity"] != group["quantity"] for g in nearby):
                        row.resolution_warnings.append("OCR passes disagree on a basket quantity.")
                    agreeing = [g for g in nearby if g["quantity"] == group["quantity"]]
                    if agreeing:
                        groups[i] = max([group, *agreeing], key=lambda g: g["confidence"])
            components = []
            previous_right = 25
            for group in groups:
                left, right = previous_right + 5, group["left"] - 5
                previous_right = group["right"]
                match = match_icon(row.body.crop((left, 0, right, row.body.height)), bank) if right > left + 10 else None
                component = {"quantity": group["quantity"], "ocr_confidence": round(group["confidence"], 2),
                             **(match or {"category": "unknown", "item": "unidentified icon", "icon_similarity": None})}
                if not match:
                    row.resolution_warnings.append("A basket icon has no confident match among the labeled tasks in these screenshots.")
                if group["confidence"] < 75:
                    row.resolution_warnings.append("A basket quantity has low OCR confidence.")
                components.append(component)
            # A remaining large graphic after the last quantity can indicate a
            # missed component. Exclude the points-star area at the far right.
            if previous_right < 810 and icon_feature(row.body.crop((previous_right + 5, 0, 840, row.body.height))) is not None:
                row.resolution_warnings.append("There may be an additional unread basket component at the right edge.")
            labels = []
            for component in components:
                label = "town visitors" if component["category"] == "town" and component["item"] == "visitors" else component["item"]
                labels.append(f"{component['quantity']} {label}")
            row.task = Task("basket", None, "mixed", "Basket: " + " + ".join(labels), components)
            row.basket_reading = OCR("\n--- alternate pass ---\n".join(evidence),
                                     round(sum(g["confidence"] for g in groups) / len(groups), 2), reading.words)


def extract_page(path: str | Path, engine: Engine, debug_dir: Path | None = None) -> Page:
    path = Path(path)
    with Image.open(path) as opened:
        image = ImageOps.exif_transpose(opened).convert("RGB")
    box = find_panel(image)
    panel = image.crop(box)
    width, height = panel.size
    a = np.asarray(panel, dtype=float)
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    green = (g > r * 1.08) & (g > b * 1.1) & (g > 80)
    purple = (r > b * .60) & (b > g * 1.12) & (r > g * 1.02) & (b > 80)
    # The blue-to-green condition separates red Xs from the orange panel/tab
    # borders, including the Bingo tab visible at the top of a scrolled log.
    marker_x = round(width * .90)
    raw_red = (r > g * 1.55) & (r > b * 1.25) & (b > g * .65) & (r > 140)
    red = np.zeros_like(raw_red)
    for lo, hi in bands(raw_red[:, marker_x:].sum(axis=1) > max(2, width * .005)):
        columns = np.flatnonzero(raw_red[lo:hi, marker_x:].sum(axis=0))
        span = int(columns[-1] - columns[0] + 1) if len(columns) else 0
        # An X is roughly square. Thin red tab borders and small fragments of
        # a header/overlay must not manufacture an extra task row.
        if hi - lo >= width * .028 and .5 <= span / (hi - lo) <= 1.8:
            red[lo:hi, marker_x:] = raw_red[lo:hi, marker_x:]
    status_masks = {"green_check": green, "purple_arrows": purple, "red_x": red}
    marker_mask = (green | purple | red)[:, marker_x:]
    marker_bands = bands(marker_mask.sum(axis=1) > max(2, width * .005))
    marker_bands = [(lo, hi) for lo, hi in marker_bands if hi - lo > width * .018]
    if not marker_bands:
        raise ValueError(f"{path.name}: No task status markers were found.")
    # OCR the header separately. It is a useful top-of-log anchor, not a task.
    head = panel.crop((0, 0, width, round(height * .45)))
    head = head.resize((1000, round(head.height * 1000 / width)), Image.Resampling.LANCZOS)
    head_text = engine.read(head, psm=11).text.lower()
    has_header = any(SequenceMatcher(None, "personalderbytasklog", re.sub(r"[^a-z]", "", line)).ratio() >= .75
                     for line in head_text.splitlines())
    centers = [(lo + hi) / 2 for lo, hi in marker_bands]
    gaps = [d for d in np.diff(centers) if width * .10 < d < width * .22]
    pitch = float(np.median(gaps)) if gaps else width * .15
    typical_marker = float(np.median([hi - lo for lo, hi in marker_bands]))
    rows = []
    warnings = []
    for candidate_index, (lo, hi) in enumerate(marker_bands):
        cy = (lo + hi) / 2
        clipped_bottom = hi - lo < typical_marker * .88 and cy > height - pitch
        if clipped_bottom and candidate_index:
            cy = centers[candidate_index - 1] + pitch
        # The row crop uses proportions of the detected panel, never screenshot pixels.
        bounds = (round(width * .153), round(cy - width * .064), round(width * .720), round(cy + width * .064))
        crop = panel.crop(bounds).resize((840, 188), Image.Resampling.LANCZOS)
        readings = read_row(engine, crop)
        best = max(readings, key=reading_score)
        task = parse_task(best.text)
        # Bright task-board buttons can resemble a checkmark in the right column.
        # Exclude only unparsed candidates above a positively identified log header.
        if not task and has_header and cy < height * .30:
            continue
        status = max(status_masks, key=lambda name: status_masks[name][lo:hi, marker_x:].sum())
        row = Row(crop, cy, hi - lo, status,
                  {"file": str(path), "row": len(rows) + 1,
                   "bbox": [box[0] + bounds[0], box[1] + bounds[1], box[0] + bounds[2], box[1] + bounds[3]]},
                  readings, task, clipped_bottom=clipped_bottom)
        body_bounds = (0, round(cy - width * .075), round(width * .73), round(cy + width * .075))
        row.body = panel.crop(body_bounds).resize((876, 180), Image.Resampling.LANCZOS)
        row.source["body_bbox"] = [box[0] + body_bounds[0], box[1] + body_bounds[1],
                                   box[0] + body_bounds[2], box[1] + body_bounds[3]]
        rows.append(row)
    if not rows:
        raise ValueError(f"{path.name}: No task rows could be extracted.")
    # Spot a cropped first text line by comparing its height to other lines in this view.
    line_sizes = []
    row_lines = []
    for row in rows:
        line_bands = bands(brown_mask(row.crop).sum(axis=1) > row.crop.width * .025)
        heights = [hi - lo for lo, hi in line_bands if hi - lo >= 3]
        row_lines.append(heights)
        line_sizes.extend(heights)
    if line_sizes and row_lines[0] and rows[0].center < pitch:
        rows[0].clipped_top = row_lines[0][0] < float(np.median(line_sizes)) * .80
    if debug_dir:
        debug_dir.mkdir(parents=True, exist_ok=True)
        panel.save(debug_dir / f"{path.stem}_panel.png")
        for i, row in enumerate(rows, 1):
            row.crop.save(debug_dir / f"{path.stem}_row_{i:02d}.png")
            if row.body is not None and row.task is None:
                row.body.save(debug_dir / f"{path.stem}_row_{i:02d}_with_icons.png")
    return Page(str(path), rows, has_header, warnings)


def row_similarity(a: Row, b: Row) -> float:
    ta, tb = a.task, b.task
    if ta and tb:
        if ta.category != tb.category:
            return 0
        if ta.category == "basket":
            signature = lambda t: [(c["category"], c["item"], c["quantity"]) for c in t.components]
            if any(c["category"] == "unknown" for c in ta.components + tb.components):
                return 0
            return 1.0 if signature(ta) == signature(tb) else 0
        if ta.quantity is not None and tb.quantity is not None and ta.quantity != tb.quantity:
            return 0
        if ta.item == tb.item:
            return 1.0
        clipped = a.clipped_bottom or b.clipped_top
        # Partial names are allowed only on visibly clipped boundary rows.
        if clipped:
            shorter, longer = sorted((ta.item, tb.item), key=len)
            similarity = SequenceMatcher(None, shorter, longer[:len(shorter)]).ratio()
            # A sliver of the next text line may itself be misread as a word.
            # Compare the intact first word too, then re-OCR the combined pixels.
            words_a = [w for w in ta.item.split() if len(w) >= 3]
            words_b = [w for w in tb.item.split() if len(w) >= 3]
            if ta.category == "production" and words_a and words_b and min(len(words_a[0]), len(words_b[0])) >= 4:
                similarity = max(similarity, SequenceMatcher(None, words_a[0], words_b[0]).ratio())
            if len(shorter) >= 3 and similarity >= .72:
                return .82 * similarity
        return 0
    sa = re.sub(r"[^a-z0-9]", "", clean(a.best.text))
    sb = re.sub(r"[^a-z0-9]", "", clean(b.best.text))
    ratio = SequenceMatcher(None, sa, sb).ratio()
    return ratio if min(len(sa), len(sb)) >= 12 and ratio >= .88 else 0


def merge_candidates(pages: list[Page], expected: int, ordered: bool = False,
                     specified_overlaps: list[int] | None = None) -> list[dict]:
    """Enumerate ordered suffix/prefix overlaps. Do not globally deduplicate tasks."""
    if not 1 <= len(pages) <= 4:
        raise ValueError("Provide 1 to 4 screenshots of one log per call.")
    if specified_overlaps is not None and (len(specified_overlaps) != len(pages) - 1 or any(k < 0 for k in specified_overlaps)):
        raise ValueError("Supply one nonnegative overlap count per adjacent pair of screenshots.")
    orders = [tuple(range(len(pages)))] if ordered or specified_overlaps is not None else itertools.permutations(range(len(pages)))
    candidates = []
    for order in orders:
        # A page containing the log title cannot follow another page with new rows.
        if any(pages[i].has_header for i in order[1:]) and not pages[order[0]].has_header:
            continue
        states = [([[row] for row in pages[order[0]].rows], [], 0.0)]
        for step, page_index in enumerate(order[1:]):
            incoming = pages[page_index].rows
            next_states = []
            for groups, overlaps, score in states:
                for k in range(min(len(groups), len(incoming)) + 1):
                    if specified_overlaps is not None and k != specified_overlaps[step]:
                        continue
                    similarities = [max(row_similarity(r, incoming[j]) for r in groups[len(groups) - k + j]) for j in range(k)]
                    if k and min(similarities) < .58:
                        continue
                    joined = [list(group) for group in groups]
                    for j in range(k):
                        joined[len(groups) - k + j].append(incoming[j])
                    joined.extend([[row] for row in incoming[k:]])
                    next_states.append((joined, overlaps + [k], score + sum(similarities)))
            states = next_states
        for groups, overlaps, score in states:
            candidates.append({"groups": groups, "order": list(order), "overlaps": overlaps,
                               "score": score, "count": len(groups)})
    if not candidates:
        raise ValueError("No consistent screenshot ordering was found. Try --ordered with images in scroll order.")
    # Visible overlap evidence outranks the expected count. Otherwise a partial
    # log could be made to look complete simply by counting a shared row twice.
    candidates.sort(key=lambda c: (c["score"], c["count"] == expected, -abs(c["count"] - expected)), reverse=True)
    return candidates


def finalize_group(group: list[Row], engine: Engine) -> dict:
    row = max(group, key=lambda r: (bool(r.basket_reading), reading_score(r.best)))
    reading = row.basket_reading or row.best
    flags = list(dict.fromkeys(row.resolution_warnings))
    reconstructed = False
    clipped = any(r.clipped_top or r.clipped_bottom for r in group)
    if len(group) > 1 and clipped:
        # Use the upper portion of the earlier view and lower portion of the later
        # view. Normalization and checkmark centers align the two crops.
        composite = group[0].crop.copy()
        seam = round(composite.height * .52)
        composite.paste(group[-1].crop.crop((0, seam, composite.width, composite.height)), (0, seam))
        attempts = read_row(engine, composite)
        combined = max(attempts, key=reading_score)
        task = parse_task(combined.text)
        known = [r.task for r in group if r.task]
        quantities = {t.quantity for t in known if t.quantity is not None}
        if task and task.quantity is not None and (not quantities or quantities == {task.quantity}) and combined.confidence >= 70:
            reading = combined
            reconstructed = True
        else:
            flags.append("Clipped overlap could not be confidently reconstructed.")
    task = row.task if row.basket_reading else parse_task(reading.text)
    if not task:
        flags.append("Task text did not match a supported English task pattern.")
    elif task.quantity is None and task.category != "basket":
        flags.append("Task quantity is unreadable.")
    if reading.confidence < 75:
        flags.append("Low OCR confidence; verify this row.")
    if reading.quantity_check and reading.quantity_check["status"] == "needs_review":
        flags.append("Quantity-only OCR could not confirm a consistent number; verify this row.")
    if clipped and not reconstructed:
        flags.append("A task boundary appears clipped; verify the full task name.")
    statuses = list(dict.fromkeys(r.status for r in group))
    if len(statuses) > 1:
        flags.append("The status symbol differs between screenshots.")
    return {
        "task": task.text if task else clean(reading.text),
        "category": task.category if task else "unknown",
        "quantity": task.quantity if task else None,
        "item": task.item if task else None,
        "components": task.components if task else [],
        "status_symbol": statuses[-1],
        "completion_status": {"green_check": "completed", "red_x": "failed"}.get(statuses[-1], "unknown"),
        "ocr_confidence": reading.confidence,
        "reconstructed_from_overlap": reconstructed,
        "needs_review": bool(flags), "warnings": flags,
        "sources": [r.source for r in group],
        "raw_ocr": [r.best.raw_text or r.best.text for r in group],
        "quantity_ocr": [r.best.quantity_check for r in group if r.best.quantity_check],
        "basket_number_ocr": row.basket_reading.text if row.basket_reading else None,
    }


def extract_log(paths: list[str | Path], expected_tasks: int = 10, ordered: bool = False,
                tesseract: str = "tesseract", debug_dir: str | Path | None = None,
                overlaps: list[int] | None = None) -> dict:
    if expected_tasks <= 0:
        raise ValueError("expected_tasks must be positive.")
    if not 1 <= len(paths) <= 4:
        raise ValueError("Provide 1 to 4 screenshots of one log per call.")
    if len({str(Path(p).resolve()) for p in paths}) != len(paths):
        raise ValueError("The same file was supplied more than once.")
    engine = Engine(tesseract)
    debug = Path(debug_dir) if debug_dir else None
    pages = [extract_page(path, engine, debug) for path in paths]
    resolve_baskets(pages, engine)
    candidates = merge_candidates(pages, expected_tasks, ordered, overlaps)
    chosen = candidates[0]
    # Different mappings with the requested count are inherently ambiguous when
    # repeated tasks occur at the screenshot boundary. Surface them for review.
    exact = [c for c in candidates if c["count"] == expected_tasks]
    warnings = [warning for page in pages for warning in page.warnings]
    if chosen["count"] != expected_tasks:
        warnings.append(f"Found {chosen['count']} tasks; expected {expected_tasks}. No rows were invented or discarded to force the count.")
    if len(exact) > 1:
        warnings.append("Several screenshot alignments produce the requested count; verify the selected order and overlaps.")
    alternatives = [c for c in candidates[1:] if c["score"] == chosen["score"] and
                    (c["order"] != chosen["order"] or c["overlaps"] != chosen["overlaps"])]
    if alternatives and len(exact) <= 1:
        warnings.append("Screenshot order or overlap is ambiguous; verify the selected mapping.")
    if not pages[chosen["order"][0]].has_header:
        warnings.append("The start-of-log title was not detected; check that the first tasks are included.")
    tasks = [dict(index=i, **finalize_group(group, engine)) for i, group in enumerate(chosen["groups"], 1)]
    if any(task["needs_review"] for task in tasks):
        warnings.append("One or more task rows need review; see their warnings.")
    return {
        "schema_version": 1, "script_version": VERSION,
        "status": "needs_review" if warnings else "ok",
        "expected_tasks": expected_tasks, "task_count": len(tasks),
        "warnings": warnings,
        "merge": {"image_order": [pages[i].source for i in chosen["order"]],
                  "overlaps": chosen["overlaps"], "exact_count_candidates": len(exact),
                  "alignment_candidates": [{"image_order": [pages[i].source for i in c["order"]],
                                            "overlaps": c["overlaps"], "task_count": c["count"]}
                                           for c in candidates[:10]]},
        "tasks": tasks,
        "screenshots": [{"file": p.source, "rows_detected": len(p.rows), "has_log_title": p.has_header} for p in pages],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("images", nargs="+", help="1 to 4 screenshots from ONE task log")
    parser.add_argument("--expected-tasks", type=int, default=10)
    parser.add_argument("--ordered", action="store_true", help="Trust input images as top-to-bottom scroll order")
    parser.add_argument("--overlaps", help="Explicit adjacent overlap counts, e.g. 1 or 1,2; implies --ordered")
    parser.add_argument("--tesseract", default="tesseract", help="Tesseract executable name or path")
    parser.add_argument("--json", dest="json_path", type=Path, help="Write detailed JSON (use '-' for stdout)")
    parser.add_argument("--debug-dir", type=Path, help="Save detected panels and row crops")
    args = parser.parse_args(argv)
    try:
        overlaps = [int(n) for n in args.overlaps.split(",")] if args.overlaps is not None else None
        result = extract_log(args.images, args.expected_tasks, args.ordered, args.tesseract, args.debug_dir, overlaps)
    except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    if args.json_path and str(args.json_path) == "-":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for task in result["tasks"]:
            suffix = " [failed]" if task["completion_status"] == "failed" else ""
            suffix += " [review]" if task["needs_review"] else ""
            print(f"{task['index']:2}. {task['task']}{suffix}")
        for warning in result["warnings"]:
            print(f"Review: {warning}", file=sys.stderr)
        if args.json_path:
            args.json_path.parent.mkdir(parents=True, exist_ok=True)
            args.json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if result["status"] == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
