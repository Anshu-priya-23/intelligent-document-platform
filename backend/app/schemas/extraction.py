from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

DocumentType = Literal["invoice", "balance_sheet", "profit_and_loss", "cash_flow_statement"]

class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

class Value(StrictModel):
    value: str | float | bool | None
    source_text: str | None
    page_number: int | None = Field(ge=1, le=3)

class Table(StrictModel):
    title: str
    columns: list[str]
    rows: list[dict[str, Value]]

class Period(StrictModel):
    label: str
    fields: dict[str, Value]
    asset_components: list[str]
    liability_components: list[str]
    asset_components_complete: bool
    liability_components_complete: bool

class Extraction(StrictModel):
    fields: dict[str, Value]
    tables: list[Table]
    periods: list[Period]
    line_items: list[dict[str, Value]]
    line_items_tax_included: bool | None = None
    tax_included: bool | None
    issues: list[str]
