"""add_training_system

Revision ID: f204b428bcd9
Revises: ce3809bb6d4e
Create Date: 2026-06-02 08:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = 'f204b428bcd9'
down_revision: Union[str, Sequence[str], None] = 'ce3809bb6d4e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    """Check if a column exists in a table"""
    bind = op.get_bind()
    result = bind.execute(
        sa.text(f"SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_NAME = :table AND COLUMN_NAME = :column AND TABLE_SCHEMA = DATABASE()"),
        {"table": table, "column": column}
    )
    return result.scalar() > 0


def upgrade() -> None:
    # ===== 修改 players 表 =====
    if not _column_exists('players', 'fatigue'):
        op.add_column('players', sa.Column('fatigue', sa.Integer(), nullable=False, server_default='0'))
    if not _column_exists('players', 'fatigue_updated_at'):
        op.add_column('players', sa.Column('fatigue_updated_at', sa.DateTime(), nullable=True))
    if not _column_exists('players', 'attribute_caps'):
        op.add_column('players', sa.Column('attribute_caps', sa.JSON(), nullable=True))
    if not _column_exists('players', 'attribute_progress'):
        op.add_column('players', sa.Column('attribute_progress', sa.JSON(), nullable=True))
    if not _column_exists('players', 'growth_peak_age'):
        op.add_column('players', sa.Column('growth_peak_age', sa.Integer(), nullable=True))
    if not _column_exists('players', 'growth_curve_type'):
        op.add_column('players', sa.Column('growth_curve_type', sa.String(length=20), nullable=True))
    if not _column_exists('players', 'growth_speed'):
        op.add_column('players', sa.Column('growth_speed', sa.DECIMAL(5, 2), nullable=False, server_default='1.00'))
    if not _column_exists('players', 'growth_stability'):
        op.add_column('players', sa.Column('growth_stability', sa.DECIMAL(5, 2), nullable=False, server_default='1.00'))
    if not _column_exists('players', 'late_bloom_factor'):
        op.add_column('players', sa.Column('late_bloom_factor', sa.DECIMAL(5, 2), nullable=False, server_default='1.00'))
    
    # ===== 新建 team_training_plans 表 =====
    bind = op.get_bind()
    result = bind.execute(sa.text("SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_NAME = 'team_training_plans' AND TABLE_SCHEMA = DATABASE()"))
    if result.scalar() == 0:
        op.create_table(
            'team_training_plans',
            sa.Column('team_id', sa.String(length=36), nullable=False),
            sa.Column('season_id', sa.String(length=36), nullable=False),
            sa.Column('season_day', sa.Integer(), nullable=False),
            sa.Column('slot', sa.Enum('morning', 'afternoon', 'evening', name='trainingslot'), nullable=False),
            sa.Column('mode', sa.Enum('team', 'groups_2', 'groups_3', name='trainingmode'), nullable=False, server_default='team'),
            sa.Column('training_item_id', sa.String(length=50), nullable=True),
            sa.Column('groups', sa.JSON(), nullable=True),
            sa.Column('status', sa.Enum('planned', 'locked', 'completed', 'missed', name='trainingplanstatus'), nullable=False, server_default='planned'),
            sa.Column('created_by', sa.Enum('player', 'ai', 'default', name='trainingcreatedby'), nullable=False, server_default='player'),
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('deleted_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['season_id'], ['seasons.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('team_id', 'season_id', 'season_day', 'slot', name='uix_training_plan_slot')
        )
        op.create_index(op.f('ix_team_training_plans_season_day'), 'team_training_plans', ['season_day'], unique=False)
        op.create_index(op.f('ix_team_training_plans_season_id'), 'team_training_plans', ['season_id'], unique=False)
        op.create_index(op.f('ix_team_training_plans_team_id'), 'team_training_plans', ['team_id'], unique=False)
    
    # ===== 新建 training_results 表 =====
    result = bind.execute(sa.text("SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_NAME = 'training_results' AND TABLE_SCHEMA = DATABASE()"))
    if result.scalar() == 0:
        op.create_table(
            'training_results',
            sa.Column('plan_id', sa.String(length=36), nullable=True),
            sa.Column('team_id', sa.String(length=36), nullable=False),
            sa.Column('player_id', sa.String(length=36), nullable=False),
            sa.Column('season_id', sa.String(length=36), nullable=False),
            sa.Column('season_day', sa.Integer(), nullable=False),
            sa.Column('slot', sa.Enum('morning', 'afternoon', 'evening', name='trainingslot'), nullable=False),
            sa.Column('training_item_id', sa.String(length=50), nullable=False),
            sa.Column('attribute_gains', sa.JSON(), nullable=True),
            sa.Column('before_attributes', sa.JSON(), nullable=True),
            sa.Column('after_attributes', sa.JSON(), nullable=True),
            sa.Column('fitness_before', sa.Integer(), nullable=False),
            sa.Column('fitness_after', sa.Integer(), nullable=False),
            sa.Column('fatigue_before', sa.Integer(), nullable=False),
            sa.Column('fatigue_after', sa.Integer(), nullable=False),
            sa.Column('load_points', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('breakthroughs', sa.JSON(), nullable=True),
            sa.Column('efficiency', sa.DECIMAL(5, 2), nullable=False, server_default='1.00'),
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')),
            sa.Column('deleted_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['plan_id'], ['team_training_plans.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['player_id'], ['players.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['season_id'], ['seasons.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_training_results_plan_id'), 'training_results', ['plan_id'], unique=False)
        op.create_index(op.f('ix_training_results_player_id'), 'training_results', ['player_id'], unique=False)
        op.create_index(op.f('ix_training_results_season_id'), 'training_results', ['season_id'], unique=False)
        op.create_index(op.f('ix_training_results_team_id'), 'training_results', ['team_id'], unique=False)
    
    # ===== 新建 team_training_ai_profiles 表 =====
    result = bind.execute(sa.text("SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_NAME = 'team_training_ai_profiles' AND TABLE_SCHEMA = DATABASE()"))
    if result.scalar() == 0:
        op.create_table(
            'team_training_ai_profiles',
            sa.Column('team_id', sa.String(length=36), nullable=False),
            sa.Column('style', sa.String(length=20), nullable=False, server_default='balanced'),
            sa.Column('risk_tolerance', sa.DECIMAL(3, 2), nullable=False, server_default='0.50'),
            sa.Column('youth_focus', sa.DECIMAL(3, 2), nullable=False, server_default='0.30'),
            sa.Column('random_seed', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('deleted_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('team_id')
        )


def downgrade() -> None:
    bind = op.get_bind()
    
    result = bind.execute(sa.text("SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_NAME = 'team_training_ai_profiles' AND TABLE_SCHEMA = DATABASE()"))
    if result.scalar() > 0:
        op.drop_table('team_training_ai_profiles')
    
    result = bind.execute(sa.text("SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_NAME = 'training_results' AND TABLE_SCHEMA = DATABASE()"))
    if result.scalar() > 0:
        op.drop_index(op.f('ix_training_results_team_id'), table_name='training_results')
        op.drop_index(op.f('ix_training_results_season_id'), table_name='training_results')
        op.drop_index(op.f('ix_training_results_player_id'), table_name='training_results')
        op.drop_index(op.f('ix_training_results_plan_id'), table_name='training_results')
        op.drop_table('training_results')
    
    result = bind.execute(sa.text("SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_NAME = 'team_training_plans' AND TABLE_SCHEMA = DATABASE()"))
    if result.scalar() > 0:
        op.drop_index(op.f('ix_team_training_plans_team_id'), table_name='team_training_plans')
        op.drop_index(op.f('ix_team_training_plans_season_id'), table_name='team_training_plans')
        op.drop_index(op.f('ix_team_training_plans_season_day'), table_name='team_training_plans')
        op.drop_table('team_training_plans')
    
    for col in ['late_bloom_factor', 'growth_stability', 'growth_speed', 'growth_curve_type', 'growth_peak_age', 'attribute_progress', 'attribute_caps', 'fatigue_updated_at', 'fatigue']:
        if _column_exists('players', col):
            op.drop_column('players', col)
