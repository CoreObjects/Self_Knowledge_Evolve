from semcore.operators.base import OperatorResult, SemanticOperator
from src.api.semantic import evidence as _mod


class EvidenceRankOperator(SemanticOperator):
    name = "evidence_rank"

    def execute(self, app, **kw) -> OperatorResult:
        data = _mod.evidence_rank(
            kw["fact_id"], kw.get("rank_by", "evidence_score"), kw.get("max_results", 10),
            store=app.store,
        )
        return OperatorResult(data=data, ontology_version=app.ontology.version())


class ConflictDetectOperator(SemanticOperator):
    name = "conflict_detect"

    def execute(self, app, **kw) -> OperatorResult:
        data = _mod.conflict_detect(
            kw["topic_node_id"], kw.get("predicate"), kw.get("min_confidence", 0.5),
            store=app.store,
        )
        return OperatorResult(data=data, ontology_version=app.ontology.version())


class FactMergeOperator(SemanticOperator):
    name = "fact_merge"

    def execute(self, app, **kw) -> OperatorResult:
        data = _mod.fact_merge(
            kw["fact_ids"], kw.get("merge_strategy", "highest_confidence"),
            kw.get("canonical_fact"),
            store=app.store,
        )
        return OperatorResult(data=data, ontology_version=app.ontology.version())