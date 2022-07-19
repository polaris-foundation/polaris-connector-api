"""empty message

Revision ID: c892fc32d49e
Revises: ef66612b5ac8
Create Date: 2018-12-11 17:14:07.817626

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "c892fc32d49e"
down_revision = "ef66612b5ac8"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column("hl7_message", "sent_at", new_column_name="sent_at_")


def downgrade():
    op.alter_column("hl7_message", "sent_at_", new_column_name="sent_at")
