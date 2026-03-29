from semcore.operators.base import OperatorResult, SemanticOperator
from src.api.semantic import expand as _mod


class ExpandOperator(SemanticOperator):
    name = "expand"

    def execute(self, app, **kw) -> OperatorResult:
        data = _mod.expand(
            kw["node_id"], kw.get("relation_types") or None,
            kw.get("depth", 1), kw.get("min_confidence", 0.5),
            kw.get("include_facts", True), kw.get("include_segments", False),
            graph=app.graph,
        )
        return OperatorResult(data=data, ontology_version=app.ontology.version())