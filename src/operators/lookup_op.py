from semcore.operators.base import OperatorResult, SemanticOperator
from src.api.semantic import lookup as _mod


class LookupOperator(SemanticOperator):
    name = "lookup"

    def execute(self, app, **kw) -> OperatorResult:
        data = _mod.lookup(
            kw["term"], kw.get("scope"), kw.get("lang", "en"),
            kw.get("ontology_version"), kw.get("include_evidence", False),
            kw.get("max_evidence", 3),
            store=app.store, graph=app.graph,
        )
        return OperatorResult(data=data, ontology_version=app.ontology.version())