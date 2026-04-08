"""align quote content nullable schema

Revision ID: 6f2b3e7a9c1d
Revises: 9a62ce7e5cff
Create Date: 2026-04-07 22:45:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6f2b3e7a9c1d"
down_revision: Union[str, Sequence[str], None] = "9a62ce7e5cff"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_CHECK_NAME = "ck_quotes_content_or_image_present"
_CHECK_SQL = "(content IS NOT NULL AND content != '') OR image_content_uuid IS NOT NULL"


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("quotes", recreate="always") as batch_op:
        batch_op.alter_column(
            "content",
            existing_type=sa.Text(),
            nullable=True,
        )
        batch_op.create_check_constraint(_CHECK_NAME, _CHECK_SQL)



def downgrade() -> None:
    """Downgrade schema."""
    op.execute(sa.text("UPDATE quotes SET content = '' WHERE content IS NULL"))
    with op.batch_alter_table("quotes", recreate="always") as batch_op:
        batch_op.drop_constraint(_CHECK_NAME, type_="check")
        batch_op.alter_column(
            "content",
            existing_type=sa.Text(),
            nullable=False,
        )
