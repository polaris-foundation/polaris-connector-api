"""msg_ctrl_id_idx

Revision ID:fdb104652cc9
Revises: 72884311b548
Create Date: 2020-06-30 14:40:57.436755

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "fdb104652cc9"
down_revision = "72884311b548"
branch_labels = None
depends_on = None


def upgrade():
    sql = """CREATE INDEX IF NOT EXISTS message_control_id_idx
    ON hl7_message USING btree
    (message_control_id ASC NULLS LAST);"""

    op.execute(sql)


def downgrade():
    sql = """DROP INDEX IF EXISTS message_control_id_idx
    ON hl7_message USING btree
    (message_control_id ASC NULLS LAST);"""
    op.execute(sql)
