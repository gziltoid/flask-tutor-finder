"""Add check constraint for booking time

Revision ID: c8267fab1e41
Revises: 9ce5ecde9476
Create Date: 2021-04-25 21:41:29.231901

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = 'c8267fab1e41'
down_revision = '9ce5ecde9476'
branch_labels = None
depends_on = None


def upgrade():
    op.create_check_constraint("ck_bookings_time_in_24h_format", "bookings",
                               "time SIMILAR TO '([01][0-9]|2[0-3]):([0-5][0-9])'")


def downgrade():
    op.drop_constraint("ck_bookings_time_in_24h_format", "bookings", type_="check")
