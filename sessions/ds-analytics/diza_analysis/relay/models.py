"""Validated API inputs. Confirmations require explicit booleans and notice versions."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class LanguageNotice(Input):
    text: str = Field(min_length=8, max_length=2000)
    question: str = Field(min_length=5, max_length=300)
    next_steps: list[str] = Field(min_length=1, max_length=8)


class BilingualNotice(Input):
    en: LanguageNotice
    es: LanguageNotice


class Keyed(Input):
    idempotency_key: str = Field(min_length=8, max_length=160)


class Publish(Keyed):
    expected_version: int = Field(ge=0)
    title: str = Field(min_length=3, max_length=160)
    content: BilingualNotice
    reason: str = Field(min_length=3, max_length=500)
    published_by: str = Field(min_length=2, max_length=80)


class Resident(Keyed):
    name: str = Field(min_length=2, max_length=100)
    language: Literal["en", "es"]
    opt_in: StrictBool


class Response(Keyed):
    notice_version: int = Field(ge=1)
    next_step: str = Field(default="", max_length=500)
    confirm_instruction: StrictBool = False
    needs_clarification: StrictBool = False
    assistance_needed: StrictBool | None = None
    assistance_details: str = Field(default="", max_length=1000)
    confirm_assistance: StrictBool = False


class TaskDecision(Keyed):
    action: Literal["accept", "complete"]
    expected_revision: int = Field(ge=1)
    owner: str = Field(min_length=2, max_length=80)


class ContactAttempt(Keyed):
    result: Literal["no_answer", "disconnected", "contacted"]


class VoiceStart(Keyed):
    language: Literal["en", "es"]
    consent_to_voice: StrictBool


class VoiceResponse(Input):
    notice_version: int = Field(ge=1)
    next_step: str = Field(default="", max_length=500)
    assistance_needed: StrictBool | None = None
    assistance_details: str = Field(default="", max_length=1000)
    confirmed: StrictBool = False
