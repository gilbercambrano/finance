from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/finanzas"
    secret_key: str = "CHANGE_ME_IN_PRODUCTION"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 días
    cookie_secure: bool = False  # poner en True en producción (requiere HTTPS)
    environment: str = "development"

    class Config:
        env_file = ".env"


settings = Settings()
