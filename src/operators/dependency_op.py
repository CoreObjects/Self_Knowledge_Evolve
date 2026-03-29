from semcore.operators.base import OperatorResult, SemanticOperator
from src.api.semantic import dependency as _mod


class DependencyOperator(SemanticOperator):
    name = "dependency_closure"

    def execute(self, app, **kw) -> OperatorResult:
        data = _mod.dependency_closure(
            kw["node_id"], kw.get("relation_types") or None,
            kw.get("max_depth", 6), kw.get("include_optional", False),
            graph=app.graph,
        )
        return OperatorResult(data=data, ontology_version=app.ontology.version())