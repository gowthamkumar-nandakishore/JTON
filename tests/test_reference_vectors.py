"""High coverage tests based on the vendored yyjson corpora."""

from __future__ import annotations

import codecs
import json
import math
import re
from pathlib import Path
from typing import Iterator

import pytest

import zson

DATA_ROOT = Path(__file__).parent / "reference_vectors"
JSON_ROOT = DATA_ROOT / "json"
NUMBER_ROOT = DATA_ROOT / "number"

_BOM_ENCODINGS: tuple[tuple[bytes, str], ...] = (
    (codecs.BOM_UTF8, "utf-8-sig"),
    (codecs.BOM_UTF16_LE, "utf-16-le"),
    (codecs.BOM_UTF16_BE, "utf-16-be"),
    (codecs.BOM_UTF32_LE, "utf-32-le"),
    (codecs.BOM_UTF32_BE, "utf-32-be"),
)

# JSONTestSuite inputs that intentionally blow recursion limits and trigger
# native crashes when parsed eagerly.
PARSING_KNOWN_CRASHERS = {
    "n_structure_100000_opening_arrays.json",
    "n_structure_open_array_object.json",
}

# Indeterminate JSONTestSuite inputs we currently skip entirely.
PARSING_Y_KNOWN_XFAILS = {
    "y_string_accepted_surrogate_pair.json",
    "y_string_accepted_surrogate_pairs.json",
    "y_string_last_surrogates_1_and_2.json",
    "y_string_surrogates_U+1D11E_MUSICAL_SYMBOL_G_CLEF.json",
    "y_string_unicode_U+10FFFE_nonchar.json",
    "y_string_unicode_U+1FFFE_nonchar.json",
}

# Invalid RFC 8259 files we intentionally accept because the ZSON parser ships
# with relaxed extensions (comments, trailing commas, unquoted keys, etc.).
PARSING_EXTENSION_ACCEPTED = {
    "n_array_extra_comma.json",
    "n_array_number_and_comma.json",
    "n_number_-NaN.json",
    "n_number_Inf.json",
    "n_number_NaN.json",
    "n_number_infinity.json",
    "n_number_minus_infinity.json",
    "n_object_non_string_key.json",
    "n_object_non_string_key_but_huge_number_instead.json",
    "n_object_repeated_null_null.json",
    "n_object_trailing_comma.json",
    "n_object_trailing_comment.json",
    "n_object_trailing_comment_slash_open.json",
    "n_object_unquoted_key.json",
    "n_string_unescaped_crtl_char.json",
    "n_string_unescaped_ctrl_char.json",
    "n_string_unescaped_newline.json",
    "n_string_unescaped_tab.json",
    "n_structure_object_with_comment.json",
}

JSON_CHECKER_RELAXED_ACCEPT = {
    "fail01_EXCLUDE.json",
    "fail03.json",
    "fail04.json",
    "fail09.json",
    "fail18_EXCLUDE.json",
    "fail25.json",
    "fail27.json",
}

EXTENSION_FAIL_TAGS = {
    "fail",
    "garbage",
    "bom",
    "str_err",
    "ext_num",
    "ext_esc",
    "ext_ws",
    "str_sq",
    "bighex",
}
EXTENSION_BIGNUM_TAG = "bignum"
TRANSFORM_KNOWN_XFAILS = {
    "string_1_escaped_invalid_codepoint.json": "unicode surrogate escape support incomplete",
    "string_2_escaped_invalid_codepoints.json": "unicode surrogate escape support incomplete",
    "string_3_escaped_invalid_codepoints.json": "unicode surrogate escape support incomplete",
}

EXTENSION_CASE_XFAILS = {
    "comment_singleline_end_cr(comment).json": "carriage-return only comment terminators unsupported",
    "content_after_doc_1(garbage).min.json": "trailing content detection pending",
    "content_after_doc_2(garbage).min.json": "trailing content detection pending",
    "content_after_doc_3(garbage).min.json": "trailing content detection pending",
    "content_after_doc_4(garbage).json": "trailing content detection pending",
    "invalid_utf8_seq_1(str_err).min.json": "UTF-8 invalid bytes normalized before parser",
    "invalid_utf8_seq_2(str_err).min.json": "UTF-8 invalid bytes normalized before parser",
    "invalid_utf8_seq_3(str_err).min.json": "UTF-8 invalid bytes normalized before parser",
    "invalid_utf8_seq_4(str_err).min.json": "UTF-8 invalid bytes normalized before parser",
    "invalid_utf8_seq_5(str_err).min.json": "UTF-8 invalid bytes normalized before parser",
    "invalid_utf8_seq_6(str_err).min.json": "UTF-8 invalid bytes normalized before parser",
    "invalid_utf8_seq_7(str_err).min.json": "UTF-8 invalid bytes normalized before parser",
    "invalid_utf8_seq_8(str_err).min.json": "UTF-8 invalid bytes normalized before parser",
    "literal_inf(inf).json": "case-insensitive Infinity handling under review",
    "literal_inf(inf).min.json": "case-insensitive Infinity handling under review",
    "literal_nan(nan).json": "case-insensitive NaN handling under review",
    "literal_nan(nan).min.json": "case-insensitive NaN handling under review",
    "str_unquoted_2(str_uq).json": "escaped sequences inside unquoted keys unsupported",
    "str_unquoted_2(str_uq).min.json": "escaped sequences inside unquoted keys unsupported",
    "str_unquoted_err_1(fail).json": "lenient unquoted key handling",
    "str_unquoted_err_1(fail).min.json": "lenient unquoted key handling",
    "str_unquoted_err_2(fail).json": "lenient unquoted key handling",
    "str_unquoted_err_2(fail).min.json": "lenient unquoted key handling",
    "str_unquoted_err_3(fail).json": "lenient unquoted key handling",
    "str_unquoted_err_3(fail).min.json": "lenient unquoted key handling",
    "str_unquoted_err_4(fail).json": "lenient unquoted key handling",
    "str_unquoted_err_4(fail).min.json": "lenient unquoted key handling",
    "unclosed_comment_1(fail).json": "unterminated comments are ignored",
    "unclosed_comment_1(fail).min.json": "unterminated comments are ignored",
    "unclosed_comment_2(fail).json": "unterminated comments are ignored",
    "unclosed_comment_2(fail).min.json": "unterminated comments are ignored",
    "unclosed_comment_3(fail).json": "unterminated comments are ignored",
    "unclosed_comment_3(fail).min.json": "unterminated comments are ignored",
    "unclosed_comment_4(fail).json": "unterminated comments are ignored",
    "unclosed_comment_4(fail).min.json": "unterminated comments are ignored",
    "unclosed_comment_5(fail).json": "unterminated comments are ignored",
    "unclosed_comment_5(fail).min.json": "unterminated comments are ignored",
    "unclosed_comment_6(fail).json": "unterminated comments are ignored",
    "unclosed_comment_6(fail).min.json": "unterminated comments are ignored",
    "unclosed_comment_7(fail).json": "unterminated comments are ignored",
    "unclosed_comment_7(fail).min.json": "unterminated comments are ignored",
    "unclosed_comment_8(fail).json": "unterminated comments are ignored",
    "unclosed_comment_8(fail).min.json": "unterminated comments are ignored",
    "unclosed_comment_tail_1(garbage).json": "unterminated comments are ignored",
    "unclosed_comment_tail_2(garbage).json": "unterminated comments are ignored",
    "unclosed_comment_tail_2(garbage).min.json": "unterminated comments are ignored",
    "whitespace_bom(bom).json": "UTF-8 BOM stripped upstream",
}

NUMBER_CASE_XFAILS = {
    "hex(ext)(big).txt": "hexadecimal numbers currently accepted",
    "hex(ext).txt": "hexadecimal numbers currently accepted",
    "hex(fail).txt": "hexadecimal numbers currently accepted",
    "int(fail).txt": "strict integer validation not enforced",
    "literal(fail).txt": "NaN payloads currently accepted",
    "literal.txt": "case-insensitive Infinity/NaN handling incomplete",
    "real(ext).txt": "extension real formats partially supported",
    "real(fail).txt": "invalid real formats accepted",
}


def _read_json_text(path: Path) -> str:
    data = path.read_bytes()
    for bom, encoding in _BOM_ENCODINGS:
        if data.startswith(bom):
            return data.decode(encoding)
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:  # pragma: no cover - executed via pytest skip
        pytest.skip(f"Unsupported encoding for {path.name}: {exc}")


def _xfail_case(case_path: Path, reasons: dict[str, str]) -> None:
    reason = reasons.get(case_path.name)
    if reason:
        pytest.xfail(reason)


def _iter_number_lines(path: Path) -> Iterator[str]:
    for raw in path.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        yield stripped


def _contains_infinite(value: object) -> bool:
    if isinstance(value, float):
        return math.isinf(value)
    if isinstance(value, list):
        return any(_contains_infinite(item) for item in value)
    if isinstance(value, dict):
        return any(_contains_infinite(item) for item in value.values())
    return False


def _contains_large_int(value: object, threshold: int = 1 << 63) -> bool:
    if isinstance(value, int):
        return abs(value) >= threshold
    if isinstance(value, list):
        return any(_contains_large_int(item, threshold) for item in value)
    if isinstance(value, dict):
        return any(_contains_large_int(item, threshold) for item in value.values())
    return False


def _collect_parsing_cases() -> list[pytest.ParameterSet]:
    cases: list[pytest.ParameterSet] = []
    for path in sorted((JSON_ROOT / "parsing").glob("*.json")):
        prefix = path.name[0]
        if prefix not in {"n", "y", "i"}:
            continue
        marks: list[pytest.MarkDecorator] = []
        if path.name in PARSING_KNOWN_CRASHERS:
            marks.append(pytest.mark.skip(reason="Input exceeds parser safeguards"))
        elif prefix == "i":
            marks.append(pytest.mark.skip(reason="Indeterminate JSONTestSuite fixture"))
        elif prefix == "y" and path.name in PARSING_Y_KNOWN_XFAILS:
            marks.append(
                pytest.mark.xfail(
                    reason="Unicode surrogate handling not implemented",
                    strict=False,
                )
            )
        cases.append(pytest.param(path, prefix, id=path.name, marks=marks))
    return cases


PARSING_CASES = _collect_parsing_cases()


@pytest.mark.parametrize("case_path,prefix", PARSING_CASES)
def test_json_parsing_corpus(case_path: Path, prefix: str) -> None:
    text = _read_json_text(case_path)
    if prefix == "y":
        reference = json.loads(text)
        result = zson.loads(text)
        assert result == reference
    else:
        if case_path.name in PARSING_EXTENSION_ACCEPTED:
            assert zson.loads(text) is not None
        else:
            with pytest.raises(ValueError):
                zson.loads(text)


@pytest.mark.parametrize(
    "case_path",
    sorted((JSON_ROOT / "checker").glob("pass*.json")),
    ids=lambda path: path.name,
)
def test_json_checker_pass_cases(case_path: Path) -> None:
    text = _read_json_text(case_path)
    assert zson.loads(text) == json.loads(text)


@pytest.mark.parametrize(
    "case_path",
    sorted((JSON_ROOT / "checker").glob("fail*.json")),
    ids=lambda path: path.name,
)
def test_json_checker_fail_cases(case_path: Path) -> None:
    text = _read_json_text(case_path)
    if case_path.name in JSON_CHECKER_RELAXED_ACCEPT:
        assert zson.loads(text) is not None
    else:
        with pytest.raises(ValueError):
            zson.loads(text)


@pytest.mark.parametrize(
    "case_path",
    sorted((JSON_ROOT / "roundtrip").glob("*.json")),
    ids=lambda path: path.name,
)
def test_roundtrip_corpus(case_path: Path) -> None:
    text = _read_json_text(case_path)
    assert zson.loads(text) == json.loads(text)


@pytest.mark.parametrize(
    "case_path",
    sorted((JSON_ROOT / "transform").glob("*.json")),
    ids=lambda path: path.name,
)
def test_transform_corpus(case_path: Path) -> None:
    _xfail_case(case_path, TRANSFORM_KNOWN_XFAILS)
    text = _read_json_text(case_path)
    assert zson.loads(text) == json.loads(text)


def _extension_tags(path: Path) -> set[str]:
    return set(re.findall(r"\(([^)]+)\)", path.stem))


def _extension_expectation(tags: set[str]) -> str:
    if tags & EXTENSION_FAIL_TAGS:
        return "fail"
    if EXTENSION_BIGNUM_TAG in tags:
        return "bignum"
    return "pass"


@pytest.mark.parametrize(
    "case_path",
    sorted((JSON_ROOT / "extensions").glob("*.json")),
    ids=lambda path: path.name,
)
def test_extension_suite(case_path: Path) -> None:
    _xfail_case(case_path, EXTENSION_CASE_XFAILS)
    tags = _extension_tags(case_path)
    expectation = _extension_expectation(tags)
    text = _read_json_text(case_path)
    if expectation == "pass":
        assert zson.loads(text) is not None
    elif expectation == "bignum":
        result = zson.loads(text)
        assert _contains_infinite(result) or _contains_large_int(result)
    else:
        with pytest.raises(ValueError):
            zson.loads(text)


def _classify_number_case(path: Path) -> str:
    tokens = set(re.findall(r"\(([^)]+)\)", path.stem))
    if "fail" in tokens or "ext" in tokens:
        return "reject"
    if "inf" in tokens:
        return "inf"
    return "accept"


NUMBER_CASES: list[pytest.ParameterSet] = []
for case_path in sorted(NUMBER_ROOT.glob("*.txt")):
    mode = _classify_number_case(case_path)
    NUMBER_CASES.append(pytest.param(case_path, mode, id=case_path.name))


@pytest.mark.parametrize("case_path,mode", NUMBER_CASES)
def test_number_reference_vectors(case_path: Path, mode: str) -> None:
    _xfail_case(case_path, NUMBER_CASE_XFAILS)
    lines = list(_iter_number_lines(case_path))
    assert lines, f"No payloads found in {case_path.name}"
    for snippet in lines:
        if mode == "accept":
            value = zson.loads(snippet)
            assert isinstance(value, (int, float))
        elif mode == "inf":
            value = zson.loads(snippet)
            if isinstance(value, float):
                assert math.isinf(value)
            else:
                assert isinstance(value, int)
                assert abs(value) >= 1 << 63
        else:
            with pytest.raises(ValueError):
                zson.loads(snippet)