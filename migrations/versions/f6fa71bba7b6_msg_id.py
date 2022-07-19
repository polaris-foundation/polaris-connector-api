"""msg_id

Revision ID: f6fa71bba7b6
Revises: c892fc32d49e
Create Date: 2018-12-19 15:28:32.535180

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f6fa71bba7b6"
down_revision = "c892fc32d49e"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "hl7_message", sa.Column("message_control_id", sa.String(), nullable=False)
    )


def downgrade():
    op.drop_column("hl7_message", "message_control_id")
