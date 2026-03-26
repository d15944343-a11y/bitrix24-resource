from .extensions import db


class BaseModel(db.Model):
    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True)


class Role(BaseModel):
    __tablename__ = "roles"

    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(255), nullable=False)

    users = db.relationship("User", back_populates="role", lazy=True)

    def __repr__(self) -> str:
        return f"<Role {self.name}>"


class User(BaseModel):
    __tablename__ = "users"

    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)

    role = db.relationship("Role", back_populates="users")

    def __repr__(self) -> str:
        return f"<User {self.email}>"
