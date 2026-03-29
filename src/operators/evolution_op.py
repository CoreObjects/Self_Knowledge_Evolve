from semcore.operators.base import OperatorResult, SemanticOperator
from src.api.semantic import evolution as _mod


class CandidateDiscoverOperator(SemanticOperator):
    name = "candidate_discover"

    def execute(self, app, **kw) -> OperatorResult:
        data = _mod.candidate_discover(
            kw["window_days"], kw.get("min_frequency", 5),
            kw.get("domain"), kw.get("min_source_count", 2),
            store=app.store,
        )
        return OperatorResult(data=data, ontology_version=app.ontology.version())


class AttachScoreOperator(SemanticOperator):
    name = "attach_score"

    def execute(self, app, **kw) -> OperatorResult:
        data = _mod.attach_score(
            kw["candidate_id"], kw.get("candidate_parent_ids") or None,
            store=app.store, graph=app.graph,
        )
        return OperatorResult(data=data, ontology_version=app.ontology.version())


class EvolutionGateOperator(SemanticOperator):
    name = "evolution_gate"

    def execute(self, app, **kw) -> OperatorResult:
        data = _mod.evolution_gate(kw["candidate_id"], store=app.store)
        return OperatorResult(data=data, ontology_version=app.ontology.version())