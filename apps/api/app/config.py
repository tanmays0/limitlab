from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    redis_url: str = "redis://localhost:6379/0"
    redis_failure_mode: str = "fail_closed"
    cors_origins: str = (
    "http://localhost:3000,http://127.0.0.1:3000,"
    "https://limitlab.vercel.app,"
    "https://limitlab-shindetanmay-gmailcoms-projects.vercel.app"
)
    api_host: str = "0.0.0.0"
    api_port: int = 8080

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

settings = Settings()
