from semcore.operators.base import OperatorResult, SemanticOperator
from src.api.semantic import path as _mod


class PathOperator(SemanticOperator):
    name = "path"

    def execute(self, app, **kw) -> OperatorResult:
        data = _mod.path_infer(
            kw["start_node_id"], kw["end_node_id"],
            kw.get("relation_policy", "all"),
            kw.get("max_hops", 5), kw.get("min_confidence", 0.5),
            graph=app.graph,
        )
        return OperatorResult(data=data, ontology_version=app.ontology.version())