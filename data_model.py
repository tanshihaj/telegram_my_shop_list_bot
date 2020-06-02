from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey

Base = declarative_base()

class List(Base):
    __tablename__ = 'list'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    is_current = Column(Boolean, nullable=False)
    tg_chat_id = Column(Integer, nullable=False)
    last_tg_msg_id = Column(Integer)

    items = relationship("Item")

    def __repr__(self):
       return "<List(name='%s', chat_id='%s')>" % (self.name, self.tg_chat_id)

class Item(Base):
    __tablename__ = 'item'

    id = Column(Integer, primary_key=True)
    list_id = Column(Integer, ForeignKey('list.id', ondelete='CASCADE'))
    name = Column(String(255), nullable=False)
    checked = Column(Boolean, nullable=False, default=False)

    def __repr__(self):
       return "<Item(name='%s', checked='%s')>" % (self.name, self.checked)

