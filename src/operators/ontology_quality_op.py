from semcore.operators.base import OperatorResult, SemanticOperator
from src.api.semantic import ontology_quality as _mod


class OntologyQualityOperator(SemanticOperator):
    name = "ontology_quality"

    def execute(self, app, **kw) -> OperatorResult:
        data = _mod.ontology_quality(store=app.store, graph=app.graph)
        return OperatorResult(data=data, ontology_version=app.ontology.version())