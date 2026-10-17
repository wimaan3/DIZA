"""Configuration; no provider credentials are exposed to the browser."""

from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class Settings:
    db_path: str
    operator_token: str = ""
    retell_enabled: bool = False
    retell_api_key: str = ""
    agent_id_en: str = ""
    agent_id_es: str = ""
    additional_agent_ids: tuple[str, ...] = ()

    @classmethod
    def from_env(cls) -> "Settings":
        base = Path(__file__).resolve().parent.parent
        path = Path(os.environ.get("RELAYLA_DB_PATH", ".data/relayla.sqlite3"))
        if not path.is_absolute():
            path = base / path
        settings = cls(
            db_path=str(path),
            operator_token=os.environ.get("RELAYLA_OPERATOR_TOKEN", ""),
            retell_enabled=os.environ.get("RELAYLA_ENABLE_RETELL", "false").lower() == "true",
            retell_api_key=os.environ.get("RETELL_API_KEY", ""),
            agent_id_en=os.environ.get("RETELL_AGENT_ID_EN", ""),
            agent_id_es=os.environ.get("RETELL_AGENT_ID_ES", ""),
            additional_agent_ids=tuple(x.strip() for x in os.environ.get("RETELL_ALLOWED_AGENT_IDS", "").split(",") if x.strip()),
        )
        if settings.retell_enabled and not settings.operator_token:
            raise ValueError("Set RELAYLA_OPERATOR_TOKEN before enabling Retell endpoints.")
        return settings

    @property
    def allowed_agent_ids(self) -> set[str]:
        return {x for x in (self.agent_id_en, self.agent_id_es, *self.additional_agent_ids) if x}

    @property
    def retell_ready(self) -> bool:
        return bool(self.retell_enabled and self.operator_token and self.retell_api_key and self.agent_id_en and self.agent_id_es)

    def public(self) -> dict:
        return {
            "retell_configured": self.retell_ready,
            "operator_token_required": bool(self.operator_token),
            "telephony": "not connected",
            "sms": "not connected",
            "voice_mode": "Retell browser voice available" if self.retell_ready else "Local simulation; Retell not configured",
        }
