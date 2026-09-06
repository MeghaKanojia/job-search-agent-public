from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://user:password@localhost:5432/job_search_agent"
    encryption_key: str = ""
    google_oauth_client_id: str = ""
    google_oauth_client_secret: str = ""
    # See pipeline/common/config.py for the free-tier caveats (Groq: ongoing
    # free tier; Gemini: free tier exists but billing removes it permanently).
    # Claude/Anthropic and Cerebras were evaluated and excluded -- neither has
    # an ongoing free tier, only a one-time trial credit.
    groq_api_key: str = ""
    gemini_api_key: str = ""
    default_llm_provider: str = "groq"
    # Gates every API route once deployed publicly -- see app/core/auth.py. This is
    # a single-user tool with no per-account system, so once the backend is a public
    # Render URL, this single shared credential is the only thing stopping anyone
    # who finds it from reading your resume PDFs (phone number, email, work
    # history), your application tracker, or burning your LLM quota / deleting data.
    dashboard_username: str = ""
    dashboard_password: str = ""
    # Comma-separated, not a JSON list -- much harder to get wrong pasting into a
    # plain-text env var box on Render than JSON-array syntax would be. Must include
    # the deployed frontend's exact origin (e.g. https://<app>.vercel.app) in
    # production; the two are on different domains there, unlike the Codespace
    # dev setup where Vite's proxy makes API calls same-origin and CORS never
    # actually applies.
    cors_allow_origins: str = "http://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()]


settings = Settings()