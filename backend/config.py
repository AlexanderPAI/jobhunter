from pydantic import Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openrouter_key: str = Field(
        ..., env="OPENROUTER_KEY", description="OpenRouter API key"
    )

    postgres_user: str = Field(
        ..., env="POSTGRES_USER", description="Postgres user name"
    )
    postgres_password: str = Field(
        ..., env="POSTGRES_PASSWORD", description="Postgres password"
    )
    postgres_host: str = Field(
        ..., env="POSTGRES_HOST", description="Postgres host name"
    )
    postgres_port: int = Field(..., env="POSTGRES_PORT", description="Postgres port")
    postgres_db: str = Field(
        ..., env="POSTGRES_DB", description="Postgres database name"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    @property
    def postgres_url(self) -> str:
        return str(
            PostgresDsn.build(
                scheme="postgresql+asyncpg",
                username=self.postgres_user,
                password=self.postgres_password,
                host=self.postgres_host,
                port=self.postgres_port,
                path=f"{self.postgres_db}",
            )
        )


cfg = Settings()
