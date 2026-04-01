from fastapi import APIRouter
from fastapi import Request

router = APIRouter(prefix="/routes", tags=["Routes"])


@router.get("/", summary="All registered API routes")
def get_routes(request: Request):
    routes = []
    for route in request.app.routes:
        if hasattr(route, "methods"):
            routes.append({
                "path"    : route.path,
                "methods" : sorted(route.methods),
                "name"    : route.name,
                "summary" : getattr(route, "summary", None),
                "tags"    : getattr(route, "tags", []),
            })

    # group by tag
    grouped = {}
    for route in routes:
        tag = route["tags"][0] if route["tags"] else "misc"
        grouped.setdefault(tag, []).append({
            "method" : route["methods"][0],
            "path"   : route["path"],
            "name"   : route["name"],
            "summary": route["summary"],
        })

    return {
        "total"  : len(routes),
        "routes" : grouped,
    }