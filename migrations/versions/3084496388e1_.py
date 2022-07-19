"""empty message

Revision ID: 3084496388e1
Revises: 
Create Date: 2018-11-22 10:43:16.929872

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "3084496388e1"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "hl7_message",
        sa.Column("uuid", sa.String(length=36), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=False),
        sa.Column("created_by_", sa.String(), nullable=False),
        sa.Column("modified", sa.DateTime(), nullable=False),
        sa.Column("modified_by_", sa.String(), nullable=False),
        sa.Column("content_raw", sa.String(), nullable=False),
        sa.Column("content_parsed", sa.String(), nullable=False),
        sa.Column("message_type", sa.String(), nullable=False),
        sa.Column("sent_datetime", sa.String(), nullable=False),
        sa.Column("is_processed", sa.Boolean(), nullable=False),
        sa.Column("src_description", sa.String(), nullable=False),
        sa.Column("dst_description", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("uuid"),
    )


def downgrade():
    op.drop_table("hl7_message")
