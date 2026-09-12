import os


class PipelineConfig:
    database_url: str = os.environ.get("DATABASE_URL", "")
    encryption_key: str = os.environ.get("ENCRYPTION_KEY", "")

    google_oauth_client_id: str = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "")
    google_oauth_client_secret: str = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "")

    # LLM providers -- see pipeline/llm/ for the multi-provider abstraction.
    # Groq: confirmed free-tier limits for openai/gpt-oss-120b are 30 req/min,
    #   8,000 tokens/min, 1,000 req/DAY. No ongoing billing risk.
    # Gemini: free tier exists but Google doesn't publish a fixed table (varies
    #   per AI Studio account) -- pipeline/llm/gemini_provider.py paces
    #   conservatively. Enabling billing on the Google Cloud project removes
    #   the free tier entirely, so never do that if you want this to stay free.
    # Claude/Anthropic and Cerebras were both evaluated and excluded: neither
    # has an ongoing free tier, only a one-time trial credit -- doesn't meet
    # this project's free-only requirement.
    # Every call site falls back to rule-based logic if a provider is unset,
    # unconfigured, or a call fails.
    groq_api_key: str = os.environ.get("GROQ_API_KEY", "")
    gemini_api_key: str = os.environ.get("GEMINI_API_KEY", "")

    # Which provider automated pipeline calls use by default. Can be overridden
    # per-call (see pipeline/llm/__init__.py's chat()) -- e.g. the dashboard's
    # cover-letter drafting lets the user pick a provider per request.
    default_llm_provider: str = os.environ.get("DEFAULT_LLM_PROVIDER", "groq")

    # Manually-obtained saved-search URL for jobs.ie/irishjobs.ie (see docs/SETUP.md --
    # these sites Disallow their RSS path in robots.txt, so this is opt-in, low-volume,
    # and gated by pipeline_settings, not a "clean" official integration).
    irish_boards_search_url: str = os.environ.get("IRISH_BOARDS_SEARCH_URL", "")

    # The original list only ever searched the plain role names, which JobSpy/Indeed/
    # LinkedIn's own ranking mostly surfaces as mid-to-senior openings for -- a
    # graduate-scheme posting titled "Graduate Data Analyst" doesn't reliably show up
    # in the top `results_wanted` results for a bare "Data Analyst" search. These
    # additional terms search for that phrasing explicitly instead of relying on it
    # to surface on its own; keyword_filter.py's role-noun+domain-qualifier match
    # already accepts these titles fine, so this was purely a search-coverage gap,
    # not a filtering one. Additive, not a replacement -- existing senior/manager
    # results keep showing up exactly as before.
    search_terms: list[str] = [
        t.strip()
        for t in os.environ.get(
            "SEARCH_TERMS",
            "Data Engineer,Data Analyst,Data Scientist,AI Engineer,ML Engineer,Analytics Engineer,"
            "Graduate Data Analyst,Graduate Data Engineer,Graduate Data Scientist,"
            "Junior Data Analyst,Junior Data Engineer,Entry Level Data Analyst",
        ).split(",")
        if t.strip()
    ]
    search_location: str = os.environ.get("SEARCH_LOCATION", "Ireland")


config = PipelineConfig()
