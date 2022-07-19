"""ack_separation

Revision ID: 0b73c56931d3
Revises: 9238dfd8809f
Create Date: 2019-06-20 11:09:28.523159

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0b73c56931d3"
down_revision = "9238dfd8809f"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("hl7_message", sa.Column("ack_uuid", sa.String(), nullable=True))


def downgrade():
    op.drop_column("hl7_message", "ack_uuid")
