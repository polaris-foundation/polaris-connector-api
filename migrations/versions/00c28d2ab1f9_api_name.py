"""api_name

Revision ID: 00c28d2ab1f9
Revises: 0b73c56931d3
Create Date: 2019-08-12 15:53:01.433094

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "00c28d2ab1f9"
down_revision = "0b73c56931d3"
branch_labels = None
depends_on = None


def upgrade():
    sql = "update failed_request_queue SET api_name='_do_send_hl7_message' where api_name='_do_send_oru_message';"
    op.execute(sql)


def downgrade():
    sql = "update failed_request_queue SET api_name='_do_send_oru_message' where api_name='_do_send_hl7_message'"
    op.execute(sql)
