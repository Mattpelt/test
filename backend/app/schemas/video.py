from datetime import datetime
from pydantic import BaseModel


class VideoUpdate(BaseModel):
    owner_id: int | None = None
    rot_id:   int | None = None


class VideoResponse(BaseModel):
    id:               int
    file_name:        str
    file_path:        str
    file_format:      str | None
    file_size_bytes:  int | None
    camera_timestamp: datetime
    owner_id:         int | None
    rot_id:           int | None
    group_id:         int | None
    matching_status:  str
    ingested_at:      datetime
    expires_at:       datetime

    class Config:
        from_attributes = True
