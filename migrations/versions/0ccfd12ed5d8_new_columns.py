"""new columns

Revision ID: 0ccfd12ed5d8
Revises: f6fa71bba7b6
Create Date: 2019-01-22 15:39:34.705340

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0ccfd12ed5d8"
down_revision = "f6fa71bba7b6"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("hl7_message", sa.Column("ack_decoded", sa.String(), nullable=True))
    op.add_column("hl7_message", sa.Column("ack_encoded", sa.String(), nullable=True))
    op.add_column(
        "hl7_message",
        sa.Column("content_encoded", sa.String(), nullable=False, server_default="sys"),
    )
    op.alter_column("hl7_message", "content_encoded", server_default=None)
    op.alter_column(
        "hl7_message", "content_parsed", existing_type=sa.VARCHAR(), nullable=True
    )
    op.alter_column(
        "hl7_message", "dst_description", existing_type=sa.VARCHAR(), nullable=True
    )
    op.alter_column(
        "hl7_message", "message_control_id", existing_type=sa.VARCHAR(), nullable=True
    )
    op.alter_column(
        "hl7_message", "message_type", existing_type=sa.VARCHAR(), nullable=True
    )
    op.alter_column(
        "hl7_message", "sent_at_", existing_type=postgresql.TIMESTAMP(), nullable=True
    )
    op.alter_column(
        "hl7_message", "src_description", existing_type=sa.VARCHAR(), nullable=True
    )
    op.alter_column(
        "hl7_message",
        "content_raw",
        existing_type=sa.VARCHAR(),
        nullable=True,
        new_column_name="content_decoded",
    )


def downgrade():
    op.alter_column(
        "hl7_message",
        "content_decoded",
        existing_type=sa.VARCHAR(),
        nullable=False,
        new_column_name="content_raw",
    )
    op.alter_column(
        "hl7_message", "src_description", existing_type=sa.VARCHAR(), nullable=False
    )
    op.alter_column(
        "hl7_message", "sent_at_", existing_type=postgresql.TIMESTAMP(), nullable=False
    )
    op.alter_column(
        "hl7_message", "message_type", existing_type=sa.VARCHAR(), nullable=False
    )
    op.alter_column(
        "hl7_message", "message_control_id", existing_type=sa.VARCHAR(), nullable=False
    )
    op.alter_column(
        "hl7_message", "dst_description", existing_type=sa.VARCHAR(), nullable=False
    )
    op.alter_column(
        "hl7_message", "content_parsed", existing_type=sa.VARCHAR(), nullable=False
    )
    op.drop_column("hl7_message", "content_encoded")
    op.drop_column("hl7_message", "ack_encoded")
    op.drop_column("hl7_message", "ack_decoded")
