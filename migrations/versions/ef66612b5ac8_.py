"""empty message

Revision ID: ef66612b5ac8
Revises: 3084496388e1
Create Date: 2018-11-22 13:46:09.979553

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "ef66612b5ac8"
down_revision = "3084496388e1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("hl7_message", sa.Column("sent_at", sa.DateTime(), nullable=False))
    op.drop_column("hl7_message", "sent_datetime")


def downgrade():
    op.add_column(
        "hl7_message",
        sa.Column("sent_datetime", sa.VARCHAR(), autoincrement=False, nullable=False),
    )
    op.drop_column("hl7_message", "sent_at")
