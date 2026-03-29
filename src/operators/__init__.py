"""All operator instances for registration in AppConfig."""

from src.operators.lookup_op       import LookupOperator
from src.operators.resolve_op      import ResolveOperator
from src.operators.expand_op       import ExpandOperator
from src.operators.filter_op       import FilterOperator
from src.operators.path_op         import PathOperator
from src.operators.dependency_op   import DependencyOperator
from src.operators.impact_op       import ImpactOperator
from src.operators.evidence_op     import EvidenceRankOperator, ConflictDetectOperator, FactMergeOperator
from src.operators.evolution_op    import CandidateDiscoverOperator, AttachScoreOperator, EvolutionGateOperator
from src.operators.search_op       import SemanticSearchOperator, EduSearchOperator

ALL_OPERATORS = [
    LookupOperator(),
    ResolveOperator(),
    ExpandOperator(),
    FilterOperator(),
    PathOperator(),
    DependencyOperator(),
    ImpactOperator(),
    EvidenceRankOperator(),
    ConflictDetectOperator(),
    FactMergeOperator(),
    CandidateDiscoverOperator(),
    AttachScoreOperator(),
    EvolutionGateOperator(),
    SemanticSearchOperator(),
    EduSearchOperator(),
]
