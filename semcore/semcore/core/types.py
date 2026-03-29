"""Core domain types — the shared vocabulary of every semcore application.

All types are plain dataclasses with no external dependencies.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Ontology layer taxonomy
# ---------------------------------------------------------------------------

class KnowledgeLayer(str, Enum):
    """Five-layer semantic structure."""
    CONCEPT   = "concept"    # 是什么  — foundational definitions
    MECHANISM = "mechanism"  # 为什么  — how / why it works
    METHOD    = "method"     # 怎么做  — operational procedures
    CONDITION = "condition"  # 何时用  — applicability rules
    SCENARIO  = "scenario"   # 在什么背景下组合应用


class SourceRank(str, Enum):
    S = "S"   # authoritative standard (RFC, IEEE, vendor official)
    A = "A"   # peer-reviewed / widely cited
    B = "B"   # reputable secondary source
    C = "C"   # unverified / community content


# ---------------------------------------------------------------------------
# Ontology model
# ---------------------------------------------------------------------------

@dataclass
class OntologyNode:
    node_id:    str
    label:      str
    layer:      KnowledgeLayer
    domain:     str                  = ""
    aliases:    list[str]            = field(default_factory=list)
    attributes: dict[str, Any]       = field(default_factory=dict)


@dataclass
class RelationDef:
    id:            str
    label:         str
    domain_layer:  KnowledgeLayer | None  = None   # None = any
    range_layer:   KnowledgeLayer | None  = None
    is_symmetric:  bool                   = False
    description:   str                    = ""


# ---------------------------------------------------------------------------
# Document / ingestion
# ---------------------------------------------------------------------------

@dataclass
class Document:
    source_doc_id: str              = field(default_factory=lambda: str(uuid.uuid4()))
    url:           str              = ""
    canonical_url: str              = ""
    site_key:      str              = ""
    source_rank:   SourceRank       = SourceRank.C
    title:         str              = ""
    doc_type:      str              = "unknown"
    language:      str              = "en"
    raw_text:      str              = ""
    content_hash:  str              = ""
    attributes:    dict[str, Any]   = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Segment / EDU  (Elementary Discourse Unit)
# ---------------------------------------------------------------------------

@dataclass
class Segment:
    """A text segment that maps 1-to-1 onto a T_EDU_DETAIL row."""
    segment_id:     str              = field(default_factory=lambda: str(uuid.uuid4()))
    source_doc_id:  str              = ""
    section_path:   list[str]        = field(default_factory=list)
    section_title:  str              = ""
    segment_index:  int              = 0
    segment_type:   str              = "unknown"
    raw_text:       str              = ""
    token_count:    int              = 0
    simhash_value:  int | None       = None
    confidence:     float            = 1.0
    attributes:     dict[str, Any]   = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Alignment
# ---------------------------------------------------------------------------

@dataclass
class Tag:
    """Result of aligning a Segment to an OntologyNode."""
    segment_id:       str
    ontology_node_id: str
    tag_type:         str              = "canonical"
    confidence:       float            = 1.0
    tagger:           str              = "rule"
    ontology_version: str              = ""


# ---------------------------------------------------------------------------
# Confidence
# ---------------------------------------------------------------------------

@dataclass
class ConfidenceScore:
    """Five-dimensional confidence model.

    Formula: 0.30×source_authority + 0.20×extraction_method +
             0.20×ontology_fit + 0.20×cross_source_consistency +
             0.10×temporal_validity
    """
    source_authority:          float = 0.5
    extraction_method:         float = 0.5
    ontology_fit:              float = 0.5
    cross_source_consistency:  float = 0.5
    temporal_validity:         float = 1.0

    def total(self) -> float:
        return (
            0.30 * self.source_authority
            + 0.20 * self.extraction_method
            + 0.20 * self.ontology_fit
            + 0.20 * self.cross_source_consistency
            + 0.10 * self.temporal_validity
        )


# ---------------------------------------------------------------------------
# Facts & evidence
# ---------------------------------------------------------------------------

@dataclass
class Fact:
    fact_id:          str              = field(default_factory=lambda: str(uuid.uuid4()))
    subject:          str              = ""
    predicate:        str              = ""
    object:           str              = ""
    domain:           str              = ""
    confidence:       ConfidenceScore  = field(default_factory=ConfidenceScore)
    qualifier:        dict[str, Any]   = field(default_factory=dict)
    lifecycle_state:  str              = "active"
    ontology_version: str              = ""


@dataclass
class Evidence:
    evidence_id:        str         = field(default_factory=lambda: str(uuid.uuid4()))
    fact_id:            str         = ""
    segment_id:         str         = ""
    source_doc_id:      str         = ""
    exact_span:         str         = ""
    span_offset_start:  int | None  = None
    span_offset_end:    int | None  = None
    source_rank:        SourceRank  = SourceRank.C
    extraction_method:  str         = "rule"
    evidence_score:     float       = 0.5


# ---------------------------------------------------------------------------
# Discourse
# ---------------------------------------------------------------------------

@dataclass
class RSTRelation:
    """RST discourse relation between two adjacent EDUs."""
    relation_id:     str   = field(default_factory=lambda: str(uuid.uuid4()))
    src_edu_id:      str   = ""
    dst_edu_id:      str   = ""
    relation_type:   str   = "Sequence"
    relation_source: str   = "rule"    # rule | llm | manual
    reliability:     int   = 1


# ---------------------------------------------------------------------------
# Ontology evolution
# ---------------------------------------------------------------------------

@dataclass
class EvolutionCandidate:
    candidate_id:              str         = field(default_factory=lambda: str(uuid.uuid4()))
    surface_forms:             list[str]   = field(default_factory=list)
    normalized_form:           str         = ""
    candidate_parent_id:       str         = ""
    source_count:              int         = 0
    source_diversity_score:    float       = 0.0
    temporal_stability_score:  float       = 0.0
    structural_fit_score:      float       = 0.0
    retrieval_gain_score:      float       = 0.0
    synonym_risk_score:        float       = 0.0
    composite_score:           float       = 0.0
    review_status:             str         = "discovered"