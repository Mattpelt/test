from datetime import date, datetime, time
from pydantic import BaseModel


class RotParticipantResponse(BaseModel):
    id:          int
    rot_id:      int
    user_id:     int | None
    afifly_name: str
    level:       str | None
    weight:      int | None
    jump_type:   str | None
    group_id:    int | None

    class Config:
        from_attributes = True


class RotResponse(BaseModel):
    id:                 int
    rot_number:         int
    day_number:         int | None
    rot_date:           date
    rot_time:           time
    plane_registration: str | None
    pilot:              str | None
    chef_avion:         str | None
    parse_status:       str
    parsed_at:          datetime

    class Config:
        from_attributes = True
