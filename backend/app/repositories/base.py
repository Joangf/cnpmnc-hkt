from typing import Any, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


async def paginate(
    session: AsyncSession, stmt: Select[tuple[T]], page: int, page_size: int
) -> tuple[list[T], int]:
    count_stmt: Select[Any] = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = await session.scalar(count_stmt)
    result = await session.scalars(
        stmt.limit(page_size)
        .offset((page - 1) * page_size)
        .execution_options(populate_existing=True)
    )
    return list(result.unique().all()), int(total or 0)
