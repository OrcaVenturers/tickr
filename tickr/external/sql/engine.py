from sqlalchemy import Engine
from sqlmodel import SQLModel, Field, Session, create_engine, select
from typing import Optional
from datetime import datetime


# Define database models
class Orders(SQLModel, table=True):
    orderId: Optional[str] = Field(primary_key=True)
    strategyId: str
    instrument: str
    orderType: str
    price: float
    reactivationDistance: float
    pointA: str
    pointB: str
    fibonacciLevel: float
    isActive: bool
    lastUpdatedAt: datetime

class ConsumerTracking(SQLModel, table=True):
    consumerId: Optional[str] = Field(default=None, primary_key=True)
    connectedAt: datetime
    disconnectedAt: Optional[datetime]
    previousOrdersTimestamp: datetime = Field(default_factory=datetime.utcnow)


connection_string = "postgresql://orca_owner:npg_an3pvgVDuZS9@ep-tiny-night-absgxyku-pooler.eu-west-2.aws.neon.tech/orca?sslmode=require"
engine_configs = {"timeout": 5}
engine: Engine = create_engine(connection_string, pool_pre_ping=True, echo=False)


# Function to create tables
def create_db_and_tables(engine: Engine):
    SQLModel.metadata.create_all(engine)


# Initialize the database
def initialize_database(engine: Engine):
    create_db_and_tables(engine)

if __name__ == "__main__":
    # Create SQLite engine
    initialize_database(engine)
