from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):

    #App
    app_name: str = "Gastronom Backend"
    app_version: str = "0.1.0"
    app_description: str = "Backend for Gastronom application"

    #Database
    database_url: str = "postgresql://user:password@localhost:5432/gastronom"

    #Clerk
    clerk_secret_key: str = ""
    clerk_jwks_url: str = "https://api.clerk.com/v1/jwks"

    #AWS
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "eu-south-1"
    aws_s3_bucket_name: str = "gastronom-product-images"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

@lru_cache

def get_settings() -> Settings:
    return Settings()