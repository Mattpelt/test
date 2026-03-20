from datetime import date, datetime, time
from pydantic import BaseModel


class RotParticipantInput(BaseModel):
    afifly_name:  str
    level:        str | None = None
    weight:       int | None = None
    jump_type:    str | None = None
    group_id:     int = 1


class RotInput(BaseModel):
    """
    Payload JSON pour créer un rot sans PDF.
    Utilisé pour les tests, le debug, et pour une éventuelle intégration
    directe avec l'API Afifly si elle devient disponible.
    """
    rot_number:         int
    day_number:         int | None = None
    rot_date:           date
    rot_time:           time
    plane_registration: str | None = None
    pilot:              str | None = None
    chef_avion:         str | None = None
    participants:       list[RotParticipantInput] = []


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
