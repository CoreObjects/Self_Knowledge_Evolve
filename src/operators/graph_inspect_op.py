from semcore.operators.base import OperatorResult, SemanticOperator
from src.api.semantic import graph_inspect as _mod


class GraphInspectOperator(SemanticOperator):
    name = "graph_inspect"

    def execute(self, app, **kw) -> OperatorResult:
        data = _mod.graph_inspect(
            kw["inspect_type"],
            threshold=kw.get("threshold", 50),
            limit=kw.get("limit", 50),
            graph=app.graph, store=app.store,
        )
        return OperatorResult(data=data, ontology_version=app.ontology.version())