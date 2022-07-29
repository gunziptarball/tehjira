import typing as t

from pydantic import BaseModel, BaseSettings


class JiraSettings(BaseModel):
    url: str
    email: str
    token: str


class Settings(BaseSettings):
    db_url: str
    jira: JiraSettings
    log_level: str = "INFO"
    local_timezone: str = "America/Chicago"
    default_project: t.Optional[str] = None

    class Config:
        env_nested_delimiter = "__"
        env_prefix = "tehjira_"
        env_file = ".env"
