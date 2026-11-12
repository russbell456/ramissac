from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    def __init__(
        self,
        db: Session,
    ):
        self.db = db

    def get_by_id(
        self,
        user_id: int,
    ) -> User | None:
        return (
            self.db.query(User)
            .filter(User.id == user_id)
            .first()
        )

    def get_by_email(
        self,
        email: str,
    ) -> User | None:
        return (
            self.db.query(User)
            .filter(User.email == email)
            .first()
        )

    def get_by_document(
        self,
        dni: str,
    ) -> User | None:
        return (
            self.db.query(User)
            .filter(User.dni == dni)
            .first()
        )

    def get_by_codigo_unico(
        self,
        codigo_unico: str,
    ) -> User | None:
        return (
            self.db.query(User)
            .filter(
                User.codigo_unico == codigo_unico
            )
            .first()
        )

    def email_exists(
        self,
        email: str,
        exclude_user_id: int | None = None,
    ) -> bool:
        query = self.db.query(User).filter(
            User.email == email
        )

        if exclude_user_id is not None:
            query = query.filter(
                User.id != exclude_user_id
            )

        return query.first() is not None

    def document_exists(
        self,
        dni: str,
        exclude_user_id: int | None = None,
    ) -> bool:
        query = self.db.query(User).filter(
            User.dni == dni
        )

        if exclude_user_id is not None:
            query = query.filter(
                User.id != exclude_user_id
            )

        return query.first() is not None

    def codigo_exists(
        self,
        codigo_unico: str,
        exclude_user_id: int | None = None,
    ) -> bool:
        query = self.db.query(User).filter(
            User.codigo_unico == codigo_unico
        )

        if exclude_user_id is not None:
            query = query.filter(
                User.id != exclude_user_id
            )

        return query.first() is not None

    def create_user(
        self,
        user: User,
    ) -> User:
        try:
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            return user

        except Exception:
            self.db.rollback()
            raise

    def update_user(
        self,
        user: User,
    ) -> User:
        try:
            self.db.commit()
            self.db.refresh(user)
            return user

        except Exception:
            self.db.rollback()
            raise

    def list_users(
        self,
        role: str | None = None,
        estado_laboral: str | None = None,
        activo: bool | None = None,
        search: str | None = None,
    ) -> list[User]:

        query = self.db.query(User)

        if role:
            query = query.filter(
                User.role == role
            )

        if estado_laboral:
            query = query.filter(
                User.estado_laboral
                == estado_laboral
            )

        if activo is not None:
            query = query.filter(
                User.activo == activo
            )

        if search:
            term = (
                f"%{search.strip()}%"
            )

            query = query.filter(
                User.nombre.ilike(term)
                | User.apellidos.ilike(term)
                | User.dni.ilike(term)
                | User.email.ilike(term)
                | User.codigo_unico.ilike(term)
            )

        return (
            query
            .order_by(
                User.apellidos.asc(),
                User.nombre.asc(),
            )
            .all()
        )

    def list_trabajadores(
        self,
    ) -> list[User]:

        return (
            self.db.query(User)
            .filter(
                User.role.in_(
                    [
                        "trabajador",
                        "almacenero",
                    ]
                ),
                User.activo.is_(True),
                User.estado_laboral
                == "activo",
            )
            .order_by(
                User.apellidos.asc()
            )
            .all()
        )