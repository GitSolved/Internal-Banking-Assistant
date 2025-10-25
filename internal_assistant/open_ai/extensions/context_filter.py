from pydantic import BaseModel, ConfigDict, Field


class ContextFilter(BaseModel):
    docs_ids: list[str] | None = Field(
        examples=[["c202d5e6-7b69-4869-81cc-dd574ee8ee11"]]
    )
    model_config = ConfigDict(arbitrary_types_allowed=True)
