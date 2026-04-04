from semcore.operators.base import OperatorResult, SemanticOperator
from src.api.semantic import ontology_inspect as _mod


class OntologyInspectOperator(SemanticOperator):
    name = "ontology_inspect"

    def execute(self, app, **kw) -> OperatorResult:
        data = _mod.ontology_inspect(
            kw["inspect_type"],
            limit=kw.get("limit", 50),
            graph=app.graph,
            store=app.store,
        )
        return OperatorResult(data=data, ontology_version=app.ontology.version())