import sqlalchemy.orm as orm
from sqlalchemy import Column, Integer, String

Base = orm.declarative_base()


class User(Base):  # type: ignore
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String)
    email = Column(String)
    phone = Column(String)
