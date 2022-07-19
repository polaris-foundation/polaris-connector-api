"""drop encoded columns

Revision ID: 750f62cf51e5
Revises: fdb104652cc9
Create Date: 2020-11-17 16:51:25.275484

"""
from alembic import op
import sqlalchemy as sa
from she_logging import logger

# revision identifiers, used by Alembic.
revision = "750f62cf51e5"
down_revision = "fdb104652cc9"
branch_labels = None
depends_on = None

REMOVE_DUPLICATES_QUERY = """
UPDATE hl7_message SET message_control_id=NULL
WHERE uuid IN (
    SELECT uuid FROM (
        SELECT uuid, ROW_NUMBER() OVER(
            PARTITION BY message_control_id
            ORDER BY sent_at_, created
        ) AS row_num
        FROM hl7_message 
    ) t
    WHERE t.row_num > 1 
);
"""


def upgrade():
    # Get rid of content_encoded, renaming content_decoded to content.
    logger.info("Migrating content")
    op.execute(
        "UPDATE hl7_message SET content_decoded = content_encoded WHERE content_decoded IS NULL"
    )
    op.alter_column("hl7_message", "content_decoded", new_column_name="content")
    op.drop_column("hl7_message", "content_encoded")

    # Get rid of ack_encoded, renaming ack_decoded to ack.
    logger.info("Migrating ack")
    op.execute(
        "UPDATE hl7_message SET ack_decoded = ack_encoded WHERE ack_decoded IS NULL"
    )
    op.alter_column("hl7_message", "ack_decoded", new_column_name="ack")
    op.drop_column("hl7_message", "ack_encoded")

    # Create a unique index on message control ID. For existing duplicates, replace message control ID with NULL
    logger.info("Migrating message control ID")
    op.execute(REMOVE_DUPLICATES_QUERY)
    op.create_index(
        op.f("ix_hl7_message_message_control_id"),
        "hl7_message",
        ["message_control_id"],
        unique=True,
    )
    op.drop_index("message_control_id_idx", table_name="hl7_message")

    # Drop unused column.
    logger.info("Dropping ack_uuid")
    op.drop_column("hl7_message", "ack_uuid")


def downgrade():
    """Don't bother filling the old _encoded rows with data."""
    op.alter_column("hl7_message", "content", new_column_name="content_decoded")
    op.alter_column("hl7_message", "ack", new_column_name="ack_decoded")
    op.add_column(
        "hl7_message",
        sa.Column("content_encoded", sa.VARCHAR(), autoincrement=False, nullable=True),
    )
    op.execute(
        "UPDATE hl7_message SET content_encoded = content_decoded WHERE content_encoded IS NULL"
    )
    op.alter_column("hl7_message", "content_encoded", nullable=False)
    op.add_column(
        "hl7_message",
        sa.Column("ack_uuid", sa.VARCHAR(), autoincrement=False, nullable=True),
    )
    op.add_column(
        "hl7_message",
        sa.Column("ack_encoded", sa.VARCHAR(), autoincrement=False, nullable=True),
    )
    op.create_index(
        "message_control_id_idx", "hl7_message", ["message_control_id"], unique=False
    )
    op.drop_index(op.f("ix_hl7_message_message_control_id"), table_name="hl7_message")
