"""Utilities for matching extract.ai results back to their source text."""

from __future__ import annotations

import difflib as _difflib
from dataclasses import dataclass as _dataclass
from fractions import Fraction as _Fraction
from typing import Any as _Any
from typing import Iterable as _Iterable

import yaml as _yaml


@_dataclass
class SourceMatch:
    """Represents the best located span for a value inside the source text."""

    start: int
    end: int
    text: str
    score: float
    variation: str | None = None

    def to_dict(self) -> dict[str, _Any]:
        return {
            "start": self.start,
            "end": self.end,
            "text": self.text,
            "score": self.score,
            "variation": self.variation,
        }


def generate_value_variants(value: float | int | str) -> list[str]:
    """Returns textual forms for a numeric value (e.g. 3100 -> ['3100', '3,100'])."""
    variants: set[str] = set()

    if isinstance(value, str):
        base_value = value
    else:
        base_value = str(value)

    variants.add(base_value)

    try:
        numeric = float(value)
        if numeric.is_integer():
            int_value = int(numeric)
            variants.add(str(int_value))
            variants.add(f"{int_value:,}")
        else:
            trimmed = (f"{numeric:.6f}").rstrip("0").rstrip(".")
            if trimmed:
                variants.add(trimmed)
            fraction = _Fraction(numeric).limit_denominator(64)
            if abs(float(fraction) - numeric) < 1e-6:
                variants.add(f"{fraction.numerator}/{fraction.denominator}")
    except (TypeError, ValueError, ZeroDivisionError):
        pass

    for variant in list(variants):
        variants.add(variant.replace(",", ""))

    return sorted({v for v in variants if v})


def generate_unit_variants(unit: str | None) -> list[str]:
    """Generates simple textual variations for units without manual dictionaries."""
    if not unit:
        return []

    base = str(unit).strip()
    variants = {
        base,
        base.lower(),
        base.upper(),
        base.capitalize(),
    }

    if base.endswith('.'):
        variants.add(base[:-1])

    if not base.lower().endswith('s'):
        variants.add(f"{base}s")
    else:
        variants.add(base[:-1])

    return sorted({v for v in variants if v})


def build_measurement_variations(value: _Any, unit: _Any) -> list[str]:
    """Create comparison strings from a measurement-like dict."""
    value_variants = generate_value_variants(value)
    unit_variants = generate_unit_variants(unit)

    combos: set[str] = set()

    for value_text in value_variants:
        combos.add(value_text)
        for unit_text in unit_variants:
            combos.add(f"{value_text} {unit_text}")
            combos.add(f"{value_text}{unit_text}")
            combos.add(f"{value_text}-{unit_text}")

    combos.update(unit_variants)

    return sorted({c.strip() for c in combos if c.strip()})


def normalize_for_matching(text: str) -> str:
    """Creates a simplified 'signature' of a string for robust matching."""
    filtered = ''.join(ch for ch in text.lower() if ch.isalnum())
    return ''.join(ch for ch in filtered if ch not in 'aeiou')


def calculate_similarity(text1: str, text2: str) -> float:
    """Calculates a similarity ratio between two strings from 0.0 to 1.0."""
    if not text1 and not text2:
        return 1.0
    if not text1 or not text2:
        return 0.0
    return _difflib.SequenceMatcher(None, text1, text2).ratio()


def _case_insensitive_positions(text: str, target: str) -> list[tuple[int, int]]:
    positions: list[tuple[int, int]] = []
    lower_text = text.lower()
    lower_target = target.lower()
    start = lower_text.find(lower_target)
    while start != -1:
        end = start + len(target)
        positions.append((start, end))
        start = lower_text.find(lower_target, start + 1)
    return positions


def find_best_variant_match(source_text: str, variants: _Iterable[str]) -> SourceMatch | None:
    best: SourceMatch | None = None
    source_text = source_text or ""
    for variant in variants:
        candidate = variant.strip()
        if not candidate:
            continue
        for start, end in _case_insensitive_positions(source_text, candidate):
            matched_text = source_text[start:end]
            score = calculate_similarity(
                normalize_for_matching(matched_text),
                normalize_for_matching(candidate)
            )
            candidate_match = SourceMatch(
                start=start,
                end=end,
                text=matched_text,
                score=score,
                variation=candidate,
            )
            if (
                best is None or
                candidate_match.score > best.score or
                (
                    candidate_match.score == best.score and
                    (candidate_match.end - candidate_match.start) > (best.end - best.start)
                )
            ):
                best = candidate_match

    if best is None:
        for variant in variants:
            candidate = variant.strip()
            if not candidate:
                continue
            matcher = _difflib.SequenceMatcher(None, source_text.lower(), candidate.lower())
            match = matcher.find_longest_match(0, len(source_text), 0, len(candidate))
            if match.size == 0:
                continue
            start = match.a
            end = start + match.size
            matched_text = source_text[start:end]
            score = calculate_similarity(
                normalize_for_matching(matched_text),
                normalize_for_matching(candidate)
            )
            candidate_match = SourceMatch(
                start=start,
                end=end,
                text=matched_text,
                score=score,
                variation=candidate,
            )
            if best is None or candidate_match.score > best.score:
                best = candidate_match

    return best


def _path_to_string(path: list[_Any]) -> str:
    components: list[str] = []
    for part in path:
        if isinstance(part, int):
            components.append(f"[{part}]")
        else:
            if components:
                components.append(".")
            components.append(str(part))
    return ''.join(components) or '$'


def _convert_source_to_text(source: _Any) -> str:
    if isinstance(source, str):
        return source
    if source is None:
        return ''
    try:
        return _yaml.dump(
            source,
            indent=2,
            sort_keys=False,
            allow_unicode=True,
            width=1000
        )
    except Exception:
        return str(source)


def _is_measurement_dict(node: _Any) -> bool:
    if not isinstance(node, dict):
        return False
    lowered = {str(k).lower() for k in node}
    if 'value' not in lowered:
        return False
    return bool({'unit', 'units', 'uom'} & lowered)


def _iter_match_targets(node: _Any, path: list[_Any] | None = None):
    if path is None:
        path = []

    if _is_measurement_dict(node):
        yield {
            'path': _path_to_string(path),
            'kind': 'measurement',
            'value': node,
        }
        return

    if isinstance(node, dict):
        for key, value in node.items():
            yield from _iter_match_targets(value, path + [key])
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _iter_match_targets(value, path + [index])
    else:
        yield {
            'path': _path_to_string(path),
            'kind': 'scalar',
            'value': node,
        }


def _normalize_match_value(value: _Any) -> str:
    if value is None:
        return ''
    if isinstance(value, (int, float)):
        return str(value)
    return str(value).strip()


def _measurement_variations(measurement: dict) -> list[str]:
    unit = None
    for key in ('unit', 'units', 'uom'):
        if key in measurement:
            unit = measurement[key]
            break
    value = measurement.get('value')
    return build_measurement_variations(value, unit)


def _scalar_variations(value: _Any) -> list[str]:
    text = _normalize_match_value(value)
    if not text:
        return []
    variants = {text}
    try:
        numeric = float(text)
    except (TypeError, ValueError):
        numeric = None

    if numeric is not None:
        variants.update(generate_value_variants(numeric))

    return sorted({v.strip() for v in variants if v.strip()})


def build_source_metadata(source: _Any, result: _Any) -> dict[str, dict[str, _Any]]:
    """Return alignment metadata for result values found in source."""
    source_text = _convert_source_to_text(source)
    metadata: dict[str, dict[str, _Any]] = {}

    for target in _iter_match_targets(result):
        path = target['path']
        kind = target['kind']
        value = target['value']

        if kind == 'measurement':
            variations = _measurement_variations(value)
        else:
            variations = _scalar_variations(value)

        if not variations:
            continue

        match = find_best_variant_match(source_text, variations)
        if match is None:
            continue

        metadata[path] = {
            'kind': kind,
            'value': value,
            'match': match.to_dict(),
        }

    return metadata
