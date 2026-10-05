"""Versioned contracts for models, environmental estimates and future field logs."""
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, model_validator


class SoilLayer(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    top_cm: float = Field(ge=0)
    bottom_cm: float = Field(gt=0, le=100000)
    label: str = Field(max_length=200)
    sand_pct: float | None = Field(default=None, ge=0, le=100)
    silt_pct: float | None = Field(default=None, ge=0, le=100)
    clay_pct: float | None = Field(default=None, ge=0, le=100)
    bulk_density_g_cm3: float | None = Field(default=None, gt=0, le=5)
    organic_carbon_g_kg: float | None = Field(default=None, ge=0, le=1000)

    @model_validator(mode="after")
    def valid_interval(self):
        if self.bottom_cm <= self.top_cm:
            raise ValueError("Layer bottom must be below its top")
        texture = [self.sand_pct, self.silt_pct, self.clay_pct]
        if all(v is not None for v in texture) and not 95 <= sum(texture) <= 105:
            raise ValueError("Texture percentages must total approximately 100")
        return self


class SoilProfile(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    schema_version: Literal[1] = 1
    site_id: str
    source_kind: Literal["unavailable", "soilgrids", "borehole", "trench", "gpr", "resistivity"]
    source: str = Field(min_length=1, max_length=1000)
    source_url: str | None = None
    retrieved_at: str | None = None
    resolution_m: float | None = Field(default=None, gt=0)
    confidence: Literal["unavailable", "model estimate", "field data supplied"]
    caveat: str = Field(min_length=1, max_length=3000)
    layers: list[SoilLayer] = Field(min_length=1, max_length=100)
    bedrock_depth_cm: float | None = Field(default=None, ge=0)
    bedrock_evidence: str | None = None
    cultural_layer_cm: tuple[float, float] | None = None
    cultural_layer_evidence: str | None = None

    @model_validator(mode="after")
    def evidence_and_order(self):
        if any(b.top_cm < a.bottom_cm for a, b in zip(self.layers, self.layers[1:])):
            raise ValueError("Layers must be ordered and non-overlapping")
        if self.bedrock_depth_cm is not None and not self.bedrock_evidence:
            raise ValueError("Bedrock requires supporting evidence")
        if self.cultural_layer_cm is not None:
            a, b = self.cultural_layer_cm
            if not 0 <= a < b <= self.layers[-1].bottom_cm or not self.cultural_layer_evidence:
                raise ValueError("Cultural depth requires a valid interval and supporting evidence")
        return self


class AssetRecord(BaseModel):
    schema_version: Literal[1] = 1
    site_id: str
    tier: Literal[1, 3]
    kind: Literal["procedural", "glb"]
    sha256: str
    generator_version: str
    confidence: str
    caveat: str
    source: str
    created_at: str
    url: str | None = None
    scene: dict | None = None


class LibraryEntry(BaseModel):
    id: str
    kind: Literal["glossary", "lesson", "reference"]
    title: str
    summary: str
    body: str = ""
    tags: list[str] = []
    references: list[str] = []
    steps: list[str] = []
    exercise: str | None = None
    url: str | None = None


class SiteProfile(BaseModel):
    id: str
    kind: Literal["site"] = "site"
    title: str
    region: str
    period: str
    typology: str
    confidence: str
    summary: str
    aliases: list[str] = []
    references: list[dict[str, str]] = []
    coordinates: tuple[float, float]
    osm_id: str
    location_quality: str
    height_m: float | None = Field(default=None, gt=0)
    height_basis: str | None = None
    checked_on: str | None = None
