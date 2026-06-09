"""add_reserve_and_injury_treatment

Revision ID: 58f064705dd1
Revises: f204b428bcd9
Create Date: 2026-06-08 07:37:24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '58f064705dd1'
down_revision: Union[str, Sequence[str], None] = 'f204b428bcd9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 扩展 TransactionSourceType enum（MySQL 需先改列类型或重建）
    # 由于 Enum 在 MySQL 中存储为 VARCHAR/ENUM，新增值可直接 ALTER
    op.execute("""
        ALTER TABLE finance_transactions 
        MODIFY COLUMN source_type 
        ENUM('broadcast','sponsor','match_bonus','cup_prize','league_prize',
             'wage','transfer','youth','penalty','manual_adjustment',
             'medical','reserve_auto_cover','reserve_settlement')
        NOT NULL
    """)
    
    # team_season_finances 增加准备金追踪字段
    op.add_column('team_season_finances', sa.Column('reserve_spent', sa.DECIMAL(15, 2), nullable=True))
    op.add_column('team_season_finances', sa.Column('reserve_auto_used', sa.DECIMAL(15, 2), nullable=True))
    op.add_column('team_season_finances', sa.Column('reserve_medical_used', sa.DECIMAL(15, 2), nullable=True))
    op.add_column('team_season_finances', sa.Column('reserve_events_used', sa.Integer(), nullable=True))
    
    # 初始化现有数据
    op.execute("UPDATE team_season_finances SET reserve_spent = 0.00 WHERE reserve_spent IS NULL")
    op.execute("UPDATE team_season_finances SET reserve_auto_used = 0.00 WHERE reserve_auto_used IS NULL")
    op.execute("UPDATE team_season_finances SET reserve_medical_used = 0.00 WHERE reserve_medical_used IS NULL")
    op.execute("UPDATE team_season_finances SET reserve_events_used = 0 WHERE reserve_events_used IS NULL")
    
    # 设为 NOT NULL
    op.alter_column('team_season_finances', 'reserve_spent', existing_type=sa.DECIMAL(15, 2), nullable=False)
    op.alter_column('team_season_finances', 'reserve_auto_used', existing_type=sa.DECIMAL(15, 2), nullable=False)
    op.alter_column('team_season_finances', 'reserve_medical_used', existing_type=sa.DECIMAL(15, 2), nullable=False)
    op.alter_column('team_season_finances', 'reserve_events_used', existing_type=sa.Integer(), nullable=False)
    
    # 新建 injury_treatments 表
    op.create_table(
        'injury_treatments',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('team_id', sa.String(36), sa.ForeignKey('teams.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('player_id', sa.String(36), sa.ForeignKey('players.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('season_id', sa.String(36), sa.ForeignKey('seasons.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('injury_record_id', sa.String(64), nullable=False, unique=True),
        sa.Column('plan', sa.Enum('enhanced', 'specialist', 'aggressive', name='treatmentplan'), nullable=False),
        sa.Column('cost', sa.DECIMAL(15, 2), nullable=False),
        sa.Column('reserve_paid', sa.DECIMAL(15, 2), default=0.00, nullable=False),
        sa.Column('cash_paid', sa.DECIMAL(15, 2), default=0.00, nullable=False),
        sa.Column('days_before', sa.Integer(), nullable=False),
        sa.Column('days_reduced', sa.Integer(), nullable=False),
        sa.Column('days_after', sa.Integer(), nullable=False),
        sa.Column('residual_wear_penalty', sa.Integer(), default=0, nullable=False),
        sa.Column('recurrence_risk_bonus', sa.DECIMAL(5, 2), default=0.00, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('injury_treatments')
    
    op.drop_column('team_season_finances', 'reserve_events_used')
    op.drop_column('team_season_finances', 'reserve_medical_used')
    op.drop_column('team_season_finances', 'reserve_auto_used')
    op.drop_column('team_season_finances', 'reserve_spent')
    
    op.execute("""
        ALTER TABLE finance_transactions 
        MODIFY COLUMN source_type 
        ENUM('broadcast','sponsor','match_bonus','cup_prize','league_prize',
             'wage','transfer','youth','penalty','manual_adjustment')
        NOT NULL
    """)
