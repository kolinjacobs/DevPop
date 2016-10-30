import sys
from sqlalchemy import  Column, ForeignKey, Integer, String

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from sqlalchemy import create_engine

Base = declarative_base()

class Items(Base):
    __tablename__ = 'items'
    name = Column(String(80), nullable  = False)
    id = Column(Integer, primary_key = True)
    description = Column(String(250))
    category = Column(String(80), nullable=False)

    @property
    def serialize(self):
        return {
            'name': self.name,
            'description': self.description,
            'id': self.id,
            'category': self.category
        }


engine = create_engine('sqlite:///Item.db')
Base.metadata.create_all(engine)