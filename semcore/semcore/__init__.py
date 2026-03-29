"""semcore — governance-first semantic knowledge infrastructure framework."""

from semcore.app import AppConfig, SemanticApp
from semcore.core.types import (
    ConfidenceScore,
    Document,
    Evidence,
    EvolutionCandidate,
    Fact,
    KnowledgeLayer,
    OntologyNode,
    RelationDef,
    RSTRelation,
    Segment,
    SourceRank,
    Tag,
)
from semcore.core.context import PipelineContext
from semcore.operators.base import (
    LoggingMiddleware,
    OperatorMiddleware,
    OperatorRegistry,
    OperatorResult,
    SemanticOperator,
    TimingMiddleware,
)
from semcore.pipeline.base import Pipeline, Stage
from semcore.providers.base import (
    EmbeddingProvider,
    GraphStore,
    LLMProvider,
    ObjectStore,
    RelationalStore,
)
from semcore.governance.base import (
    ConfidenceScorer,
    Conflict,
    ConflictDetector,
    EvolutionGate,
    GateResult,
)
from semcore.ontology.base import OntologyProvider

__version__ = "0.1.0"
__all__ = [
    # App
    "AppConfig", "SemanticApp",
    # Types
    "KnowledgeLayer", "SourceRank",
    "OntologyNode", "RelationDef",
    "Document", "Segment", "Tag",
    "ConfidenceScore", "Fact", "Evidence",
    "RSTRelation", "EvolutionCandidate",
    # Context
    "PipelineContext",
    # Pipeline
    "Pipeline", "Stage",
    # Operators
    "SemanticOperator", "OperatorResult", "OperatorRegistry",
    "OperatorMiddleware", "TimingMiddleware", "LoggingMiddleware",
    # Governance
    "ConfidenceScorer", "Conflict", "ConflictDetector",
    "EvolutionGate", "GateResult",
    # Ontology
    "OntologyProvider",
    # Providers
    "LLMProvider", "EmbeddingProvider",
    "GraphStore", "RelationalStore", "ObjectStore",
]