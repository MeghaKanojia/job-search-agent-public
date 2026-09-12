from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import analytics, applications, documents, matches, profile, settings as settings_routes
from app.core.auth import require_auth
from app.core.config import settings

app = FastAPI(title="Job Search Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Every actual data route requires DASHBOARD_USERNAME/DASHBOARD_PASSWORD (see
# app/core/auth.py) -- this is a single-user tool with no other access control
# once deployed publicly. /health is deliberately excluded: it returns nothing
# sensitive and Render's own health checks need to reach it unauthenticated.
_auth_dep = [Depends(require_auth)]
app.include_router(matches.router, dependencies=_auth_dep)
app.include_router(applications.router, dependencies=_auth_dep)
app.include_router(documents.router, dependencies=_auth_dep)
app.include_router(profile.router, dependencies=_auth_dep)
app.include_router(settings_routes.router, dependencies=_auth_dep)
app.include_router(analytics.router, dependencies=_auth_dep)


@app.get("/health")
def health():
    return {"status": "ok"}
