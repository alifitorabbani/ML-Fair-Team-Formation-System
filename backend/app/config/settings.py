import os
from pydantic_settings import BaseSettings
from typing import Optional, List, Any


class Settings(BaseSettings):
    app_name: str = "ML Fair Team Formation System"
    debug: bool = True
    secret_key: str = "dev-secret-key-change-in-production"
    database_url: str = "sqlite+aiosqlite:///./ml_fair_teams.db"
    upload_dir: str = "./uploads"
    max_upload_size: int = 10 * 1024 * 1024
    frontend_url: str = "http://localhost:3636"
    cors_origins: str = ""
    max_optimization_iterations: int = 300
    min_fairness_threshold: float = 85.0
    default_random_seed: int = 42
    current_rank_weight: float = 0.40
    current_star_weight: float = 0.20
    highest_rank_weight: float = 0.25
    highest_star_weight: float = 0.15
    alpha_skill_imbalance: float = 1.0
    beta_role_imbalance: float = 1.5
    gamma_comfort_penalty: float = 0.8
    delta_flexibility_penalty: float = 0.5
    payment_method: str = "E-Money Dana/Link"
    payment_account_number: str = "082141233543"
    payment_account_name: str = "Muhammad Syofiudin"
    payment_amount: int = 20000
    master_csv_path: str = "data/Database-Fix-WMPL-S3.csv"
    blob_read_write_token: str = ""
    admin_emails: str = "rebanialifito@gmail.com,rabbanialifito@gmail.com"

    @property
    def cors_origins_list(self) -> List[str]:
        origins = [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        if origins:
            return origins
        return [self.frontend_url] if self.frontend_url else []

    @property
    def admin_emails_list(self) -> List[str]:
        return [e.strip().lower() for e in self.admin_emails.split(",") if e.strip()]

    def model_post_init(self, __context: Any) -> None:
        if os.getenv("VERCEL") == "1":
            if not self.database_url or self.database_url.startswith("sqlite"):
                if "///./" in self.database_url or "//./" in self.database_url:
                    self.database_url = "sqlite+aiosqlite:////tmp/ml_fair_teams.db"
            if not self.upload_dir or self.upload_dir in ("./uploads", "uploads"):
                self.upload_dir = "/tmp/uploads"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
