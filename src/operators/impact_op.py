from semcore.operators.base import OperatorResult, SemanticOperator
from src.api.semantic import impact as _mod


class ImpactOperator(SemanticOperator):
    name = "impact_propagate"

    def execute(self, app, **kw) -> OperatorResult:
        data = _mod.impact_propagate(
            kw["event_node_id"], kw.get("event_type", "fault"),
            kw.get("relation_policy", "causal"),
            kw.get("max_depth", 4), kw.get("min_confidence", 0.6),
            kw.get("context", {}),
            graph=app.graph,
        )
        return OperatorResult(data=data, ontology_version=app.ontology.version())