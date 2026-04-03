from semcore.operators.base import OperatorResult, SemanticOperator
from src.api.semantic import stale_knowledge as _mod


class StaleKnowledgeOperator(SemanticOperator):
    name = "stale_knowledge"

    def execute(self, app, **kw) -> OperatorResult:
        data = _mod.stale_knowledge(
            query_type=kw.get("type", "fact"),
            days=kw.get("days", 90),
            limit=kw.get("limit", 50),
            store=app.store,
        )
        return OperatorResult(data=data, ontology_version=app.ontology.version())