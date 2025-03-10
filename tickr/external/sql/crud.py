from sqlalchemy import Engine
from sqlmodel import SQLModel, Field, Session, create_engine, select
from typing import Optional
from datetime import datetime
from tickr.external.sql.engine import engine, Orders, ConsumerTracking


# CRUD Operations
def add_order(engine: Engine, order: Orders):
    with Session(engine) as session:
        session.add(order)
        session.commit()
        session.refresh(order)
    return order

def get_order(engine: Engine, order_id: int):
    with Session(engine) as session:
        return session.get(Orders, order_id)


def create_or_update_order(engine, order: Orders):
    with Session(engine) as session:
        statement = select(Orders).where((Orders.strategyId == order.strategyId) & (Orders.fibonacciLevel == order.fibonacciLevel))
        existing_order = session.exec(statement).first()
        if existing_order:
            for key, value in order.model_dump().items():
                setattr(existing_order, key, value)
            existing_order.lastUpdatedAt = datetime.utcnow()
        else:
            order.lastUpdatedAt = datetime.utcnow()
            session.add(order)
        session.commit()
        session.refresh(existing_order if existing_order else order)
        return existing_order if existing_order else order



def update_order(engine: Engine, order_id: int, **kwargs):
    with Session(engine) as session:
        order = session.get(Orders, order_id)
        if order:
            for key, value in kwargs.items():
                setattr(order, key, value)
            session.commit()
            session.refresh(order)
        return order

def delete_order(engine: Engine, order_id: int):
    with Session(engine) as session:
        order = session.get(Orders, order_id)
        if order:
            session.delete(order)
            session.commit()
        return order

def add_consumer_tracking(engine: Engine, consumer: ConsumerTracking):
    with Session(engine) as session:
        session.add(consumer)
        session.commit()
        session.refresh(consumer)
    return consumer

def get_consumer_tracking(engine: Engine, consumer_id: int):
    with Session(engine) as session:
        return session.get(ConsumerTracking, consumer_id)

def update_consumer_tracking(engine: Engine, consumer_id: int, **kwargs):
    with Session(engine) as session:
        consumer = session.get(ConsumerTracking, consumer_id)
        if consumer:
            for key, value in kwargs.items():
                setattr(consumer, key, value)
            session.commit()
            session.refresh(consumer)
        return consumer

def delete_consumer_tracking(engine: Engine, consumer_id: int):
    with Session(engine) as session:
        consumer = session.get(ConsumerTracking, consumer_id)
        if consumer:
            session.delete(consumer)
            session.commit()
        return consumer

