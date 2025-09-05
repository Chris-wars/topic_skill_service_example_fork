import uuid
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import UUID

db = SQLAlchemy()

def gen_uuid():
    return str(uuid.uuid4())

class Topic(db.Model):
    __tablename__ = "topics"

    id = db.Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    name = db.Column(db.String, nullable=False)
    description = db.Column(db.Text)
    parent_topic_id = db.Column(UUID(as_uuid=False), db.ForeignKey("topics.id"), nullable=True)
 
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "parentTopicID": self.parent_topic_id
        }