from semcore.operators.base import OperatorResult, SemanticOperator
from src.api.semantic import context_assemble as _mod


class ContextAssembleOperator(SemanticOperator):
    name = "context_assemble"

    def execute(self, app, **kw) -> OperatorResult:
        data = _mod.context_assemble(
            node_ids=kw.get("node_ids"),
            keywords=kw.get("keywords"),
            max_segments=kw.get("max_segments", 50),
            max_hops=kw.get("max_hops", 2),
            store=app.store,
            graph=app.graph,
        )
        return OperatorResult(data=data, ontology_version=app.ontology.version())