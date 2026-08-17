"""add provider_events and offer_sessions tables

Revision ID: c4d5e6f7a8b9
Revises: b9f2a4c1e6d7
Create Date: 2026-08-14 14:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'c4d5e6f7a8b9'
down_revision: Union[str, None] = 'b9f2a4c1e6d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'provider_events',
        sa.Column('provider_id', sa.String(36), nullable=False),
        sa.Column('event_type', sa.String(40), nullable=False),
        sa.Column('request_id', sa.String(120), nullable=False),
        sa.Column('raw_payload', sa.Text(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('result', sa.Text(), nullable=False),
        sa.Column('source_ip', sa.String(45), nullable=False),
        sa.Column('meta', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('id', sa.String(36), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_provider_events_created_at'), 'provider_events', ['created_at'], unique=False)
    op.create_index(op.f('ix_provider_events_event_type'), 'provider_events', ['event_type'], unique=False)
    op.create_index(op.f('ix_provider_events_provider_id'), 'provider_events', ['provider_id'], unique=False)
    op.create_index(op.f('ix_provider_events_request_id'), 'provider_events', ['request_id'], unique=False)

    op.create_table(
        'offer_sessions',
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('offer_id', sa.String(36), nullable=False),
        sa.Column('provider_id', sa.String(36), nullable=False),
        sa.Column('click_id', sa.String(36), nullable=False),
        sa.Column('session_token', sa.String(120), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('ip', sa.String(45), nullable=False),
        sa.Column('device_id', sa.String(64), nullable=False),
        sa.Column('converted_at', sa.String(40), nullable=False),
        sa.Column('conversion_id', sa.String(36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('id', sa.String(36), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_offer_sessions_click_id'), 'offer_sessions', ['click_id'], unique=True)
    op.create_index(op.f('ix_offer_sessions_conversion_id'), 'offer_sessions', ['conversion_id'], unique=False)
    op.create_index(op.f('ix_offer_sessions_created_at'), 'offer_sessions', ['created_at'], unique=False)
    op.create_index(op.f('ix_offer_sessions_offer_id'), 'offer_sessions', ['offer_id'], unique=False)
    op.create_index(op.f('ix_offer_sessions_provider_id'), 'offer_sessions', ['provider_id'], unique=False)
    op.create_index(op.f('ix_offer_sessions_session_token'), 'offer_sessions', ['session_token'], unique=True)
    op.create_index(op.f('ix_offer_sessions_status'), 'offer_sessions', ['status'], unique=False)
    op.create_index(op.f('ix_offer_sessions_user_id'), 'offer_sessions', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_table('offer_sessions')
    op.drop_table('provider_events')
