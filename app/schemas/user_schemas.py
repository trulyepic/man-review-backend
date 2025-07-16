
from pydantic import BaseModel, EmailStr, field_validator


class UserCreate(BaseModel):
    username: str
    password: str
    email: EmailStr

    # @field_validator("email")
    @classmethod
    def validate_email_domain(cls, v):
        if not (v.endswith("@gmail.com") or v.endswith("@yahoo.com")):
            raise ValueError("Only Gmail or Yahoo emails are accepted")
        return v

class UserOut(BaseModel):
    id: int
    username: str
    role: str

class SignupResponse(BaseModel):
    message: str
    token: str

class UserLogin(BaseModel):
    username: str
    password: str


