"""Explicit public BCB records, not arbitrary JSON metadata or truth votes.

BCB documents these endpoints at ``COPOM_SCHEMA_URL``.  The index only locates
a meeting; its title is never body evidence.  A detail response must agree on
both meeting number and reference date before its published HTML is exposed.
The reference date remains separately typed: it is NOT injected into a quote,
silently converted to a meeting date, or treated as an independent source.

This module performs no HTTP requests.  Callers must use public_fetch with the
limits below, account for every request in the existing retrieval budget, and
feed returned HTML through the ordinary visible-article parser.  This module
does not make an unavailable second source or bypass comparison/claim guards.
"""

from dataclasses import dataclass
from datetime import date
from html import escape
import json
import re

from app.services.public_fetch import FetchedResource


COPOM_SCHEMA_URL = "https://www.bcb.gov.br/conteudo/dadosabertos/BCBDeinf/copom.yaml"
COPOM_API_BASE = "https://www.bcb.gov.br/api/servico/sitebcb/copom"
COPOM_INDEX_LIMIT = 100
COPOM_INDEX_URL = COPOM_API_BASE + f"/comunicados?quantidade={COPOM_INDEX_LIMIT}"
COPOM_MAX_BYTES = 256 * 1024
COPOM_ALLOWED_TYPES = frozenset({"application/json"})
COPOM_REFERENCE_DATE_SEMANTICS = "bcb_comunicado_publication_reference_date"


class OfficialSourceBodyError(ValueError):
    """An explicit official endpoint did not satisfy its bounded schema."""


@dataclass(frozen=True)
class CopomRecordReference:
    meeting_number: int
    reference_date: str
    title: str


@dataclass(frozen=True)
class OfficialSourceBody:
    resource: FetchedResource
    meeting_number: int
    reference_date: str
    reference_date_semantics: str = COPOM_REFERENCE_DATE_SEMANTICS
    record_kind: str = "bcb_copom_comunicado"
    schema_url: str = COPOM_SCHEMA_URL

    @property
    def official_record(self):
        """Typed provenance for an explicit downstream policy, not a vote."""
        return {
            "kind": self.record_kind,
            "record_id": str(self.meeting_number),
            "record_url": self.resource.final_url,
            "record_reference_date": self.reference_date,
            "reference_date_semantics": self.reference_date_semantics,
            "schema_url": self.schema_url,
            "discovery_url": COPOM_INDEX_URL,
        }


def _iso_date(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise OfficialSourceBodyError("Invalid BCB reference date")
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise OfficialSourceBodyError("Invalid BCB reference date") from exc
    return value


def _meeting_number(value):
    if type(value) is not int or not 1 <= value <= 5000:
        raise OfficialSourceBodyError("Invalid BCB meeting number")
    return value


def _title(value):
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= 1000:
        raise OfficialSourceBodyError("Invalid BCB title")
    return value


def copom_detail_url(reference):
    """Fixed origin/path; neither titles nor claimed text can supply a URL."""
    if not isinstance(reference, CopomRecordReference):
        raise OfficialSourceBodyError("Invalid BCB record reference")
    number = _meeting_number(reference.meeting_number)
    _iso_date(reference.reference_date)
    _title(reference.title)
    return COPOM_API_BASE + f"/comunicados_detalhes?nro_reuniao={number}"


def _no_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise OfficialSourceBodyError("Duplicate JSON field in BCB response")
        result[key] = value
    return result


def _rows(resource, expected_url, maximum):
    if (not isinstance(resource, FetchedResource)
            or resource.final_url != expected_url
            or resource.content_type not in COPOM_ALLOWED_TYPES
            or not 0 < len(resource.data) <= COPOM_MAX_BYTES):
        raise OfficialSourceBodyError("Unexpected BCB response boundary")
    try:
        payload = json.loads(resource.data.decode("utf-8"), object_pairs_hook=_no_duplicate_keys)
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise OfficialSourceBodyError("Invalid BCB response JSON") from exc
    if (not isinstance(payload, dict) or set(payload) != {"conteudo"}
            or not isinstance(payload["conteudo"], list)
            or len(payload["conteudo"]) > maximum):
        raise OfficialSourceBodyError("Unexpected BCB response schema")
    return payload["conteudo"]


def select_copom_reference(resource, reference_date):
    """Find one exact official date, never the nearest/current meeting.

    ``reference_date`` must come from a separately validated literal query.
    Its presence here is a discovery key, not proof that the query is true.
    No result on absence.  Duplicate dates/numbers or malformed rows fail
    closed rather than selecting a convenient record.
    """
    requested = _iso_date(reference_date)
    rows = _rows(resource, COPOM_INDEX_URL, COPOM_INDEX_LIMIT)
    seen_dates, seen_numbers, selected = set(), set(), None
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"nro_reuniao", "dataReferencia", "titulo"}:
            raise OfficialSourceBodyError("Unexpected BCB index row")
        number = _meeting_number(row["nro_reuniao"])
        stamp = _iso_date(row["dataReferencia"])
        title = _title(row["titulo"])
        if stamp in seen_dates or number in seen_numbers:
            raise OfficialSourceBodyError("Ambiguous BCB index record")
        seen_dates.add(stamp)
        seen_numbers.add(number)
        if stamp == requested:
            selected = CopomRecordReference(number, stamp, title)
    return selected


def decode_copom_body(resource, reference):
    """Expose documented ``textoComunicado`` only after exact record binding.

    Synthetic structural wrapper contains no added decision/date sentence.
    Heading remains context; original body HTML is preserved for the regular
    static visible-text parser, including its hidden/script/caption exclusions.
    """
    expected_url = copom_detail_url(reference)
    rows = _rows(resource, expected_url, 1)
    if len(rows) != 1 or not isinstance(rows[0], dict):
        raise OfficialSourceBodyError("Missing BCB detail record")
    row = rows[0]
    if set(row) != {"nro_reuniao", "dataReferencia", "titulo", "textoComunicado"}:
        raise OfficialSourceBodyError("Unexpected BCB detail row")
    if (_meeting_number(row["nro_reuniao"]) != reference.meeting_number
            or _iso_date(row["dataReferencia"]) != reference.reference_date):
        raise OfficialSourceBodyError("Mismatched BCB detail record")
    title = _title(row["titulo"])
    body = row["textoComunicado"]
    if not isinstance(body, str) or not body.strip():
        raise OfficialSourceBodyError("Missing BCB detail body")
    markup = "<html><body><article><h1>" + escape(title) + "</h1>" + body + "</article></body></html>"
    return OfficialSourceBody(
        resource=FetchedResource(markup.encode("utf-8"), "text/html", expected_url, "utf-8"),
        meeting_number=reference.meeting_number,
        reference_date=reference.reference_date,
    )
