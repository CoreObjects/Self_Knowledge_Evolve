from semcore.operators.base import OperatorResult, SemanticOperator
from src.api.semantic import cross_layer_check as _mod


class CrossLayerCheckOperator(SemanticOperator):
    name = "cross_layer_check"

    def execute(self, app, **kw) -> OperatorResult:
        data = _mod.cross_layer_check(
            source_layer=kw.get("source_layer"),
            target_layer=kw.get("target_layer"),
            gaps=kw.get("gaps", False),
            limit=kw.get("limit", 50),
            graph=app.graph,
        )
        return OperatorResult(data=data, ontology_version=app.ontology.version())