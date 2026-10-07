import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "IsoAPA"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"
    DEBUG: bool = True
    CORS_ALLOWED_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"
    TRUSTED_HOSTS: str = "localhost,127.0.0.1,0.0.0.0,backend,isoapa.sls.cuhk.edu.hk"
    
    DATABASE_URL: str = "sqlite:///" + os.path.join(os.path.dirname(os.path.dirname(__file__)), "isoapa.db")

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() in {"prod", "production"}

    @property
    def cors_allowed_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.CORS_ALLOWED_ORIGINS.split(",")
            if origin.strip()
        ]

    @property
    def trusted_hosts(self) -> list[str]:
        return [
            host.strip()
            for host in self.TRUSTED_HOSTS.split(",")
            if host.strip()
        ]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
