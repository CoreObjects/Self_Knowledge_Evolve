from semcore.operators.base import OperatorResult, SemanticOperator
from src.api.semantic import resolve as _mod


class ResolveOperator(SemanticOperator):
    name = "resolve"

    def execute(self, app, **kw) -> OperatorResult:
        data = _mod.resolve(
            kw["alias"], kw.get("scope"), kw.get("vendor"),
            store=app.store, graph=app.graph,
        )
        return OperatorResult(data=data, ontology_version=app.ontology.version())