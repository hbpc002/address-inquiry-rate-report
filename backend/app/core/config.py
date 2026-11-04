from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    PROJECT_NAME: str = "客户服务中心运营管理平台"
    DATABASE_URL: str = "postgresql://postgres:admin123%40kf@localhost:5432/schedule"
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    # 日志保留天数，默认3个月
    LOG_RETENTION_DAYS: int = 90
    # 旧页面（非营销）固定数据范围：热线运营组，包含其下所有子部门
    LEGACY_SCOPE_DEPT_PATH: str = "广西分公司>>省中心>>客户服务营销中心>>热线运营组"

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()
