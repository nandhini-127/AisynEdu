"""add user streaks and last_login_date

Revision ID: 003_user_streaks
Revises: 002_analytics_events
Create Date: 2026-11-14 15:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '003_user_streaks'
down_revision: Union[str, None] = '002_analytics_events'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add columns to users table
    op.add_column(
        'users',
        sa.Column('current_streak', sa.Integer(), nullable=False, server_default='0')
    )
    op.add_column(
        'users',
        sa.Column('longest_streak', sa.Integer(), nullable=False, server_default='0')
    )
    op.add_column(
        'users',
        sa.Column('last_login_date', sa.Date(), nullable=True)
    )

    # 2. Safely populate existing users' streak data without hardcoded values
    # If a user previously logged in (last_login is not null), initialize last_login_date and streak=1
    op.execute("""
        UPDATE users
        SET last_login_date = (last_login AT TIME ZONE 'Asia/Kolkata')::date,
            current_streak = 1,
            longest_streak = 1
        WHERE last_login IS NOT NULL;
    """)


def downgrade() -> None:
    op.drop_column('users', 'last_login_date')
    op.drop_column('users', 'longest_streak')
    op.drop_column('users', 'current_streak')

