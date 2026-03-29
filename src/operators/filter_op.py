from semcore.operators.base import OperatorResult, SemanticOperator
from src.api.semantic import filter as _mod


class FilterOperator(SemanticOperator):
    name = "filter"

    def execute(self, app, **kw) -> OperatorResult:
        data = _mod.filter_objects(
            kw["object_type"], kw.get("filters", {}),
            kw.get("sort_by", "confidence"), kw.get("sort_order", "desc"),
            kw.get("page", 1), kw.get("page_size", 20),
            store=app.store, graph=app.graph,
        )
        return OperatorResult(data=data, ontology_version=app.ontology.version())