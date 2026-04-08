"""enforce current nickname uniqueness

Revision ID: b1d3c6f4a2e9
Revises: 6f2b3e7a9c1d
Create Date: 2026-04-08 03:08:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b1d3c6f4a2e9"
down_revision: Union[str, Sequence[str], None] = "6f2b3e7a9c1d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_USER_INDEX_NAME = "uq_user_nicknames_current_using"
_GROUP_INDEX_NAME = "uq_group_nicknames_current_using"
_PARTIAL_CURRENT_WHERE = sa.text("current_using = 1")


def _cleanup_user_nickname_currents() -> None:
    op.execute(
        sa.text(
            """
            UPDATE user_nicknames
            SET current_using = 0
            WHERE current_using = 1
              AND rowid NOT IN (
                  SELECT MIN(rowid)
                  FROM user_nicknames
                  WHERE current_using = 1
                  GROUP BY qq_id
              )
            """
        )
    )


def _cleanup_group_nickname_currents() -> None:
    op.execute(
        sa.text(
            """
            UPDATE group_nicknames
            SET current_using = 0
            WHERE current_using = 1
              AND rowid NOT IN (
                  SELECT MIN(rowid)
                  FROM group_nicknames
                  WHERE current_using = 1
                  GROUP BY qq_id, group_id
              )
            """
        )
    )


def upgrade() -> None:
    """Upgrade schema."""
    _cleanup_user_nickname_currents()
    _cleanup_group_nickname_currents()

    op.create_index(
        _USER_INDEX_NAME,
        "user_nicknames",
        ["qq_id"],
        unique=True,
        sqlite_where=_PARTIAL_CURRENT_WHERE,
    )
    op.create_index(
        _GROUP_INDEX_NAME,
        "group_nicknames",
        ["qq_id", "group_id"],
        unique=True,
        sqlite_where=_PARTIAL_CURRENT_WHERE,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(_GROUP_INDEX_NAME, table_name="group_nicknames")
    op.drop_index(_USER_INDEX_NAME, table_name="user_nicknames")
