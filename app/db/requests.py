from app.db.models import User, UserItem, async_session
from sqlalchemy import select, delete, update

# async def get_categories():
#     async with async_session() as session:
#         result = await session.scalars(select(Category))
#         return result


async def set_useritem(userdata: dict, itemdata: dict):
    """
    userdata:
    {
      'tg_id': int,
      'username': str,
    }
    itemdatra:
    {
        'username': str,
        'name': str,
        'date': str,
    }
    """
    async with async_session() as session:
        result = await session.execute(select(User).where(User.tg_id == userdata['tg_id']))
        user = result.scalars().first()

        if not user:
            user = User(tg_id=userdata['tg_id'], username=userdata.get('username'))
            session.add(user)
            await session.flush()  # Чтобы получить user.id

        useritem = UserItem(
            username=itemdata.get('username'),
            name=itemdata.get('name'),
            date=itemdata.get('date', ''),
            user=user
        )
        session.add(useritem)
        await session.commit()

async def update_user_item(
    date_id: int,
    itemdata
) -> bool:
    if not itemdata:
        return False

    async with async_session() as session:
        async with session.begin():
            stmt = (
                update(UserItem)
                .where(UserItem.id == date_id)
                .values(username=itemdata.get('username'), name=itemdata.get('name'), date=itemdata.get('date'))
                .execution_options(synchronize_session="fetch")
            )
            
            result = await session.execute(stmt)
            await session.commit()
            
            return result.rowcount > 0

PAGE_SIZE = 6  # сколько дат загружаем за раз

async def get_user_items_block(tg_id: int, page: int = 0):
    """
    Получаем UserItem пользователя порциями (блоками)
    """
    offset = page * PAGE_SIZE
    async with async_session() as session:
        result = await session.execute(
            select(UserItem)
            .join(User, User.id == UserItem.user_id)
            .where(User.tg_id == tg_id)
            .order_by(UserItem.id)   # сортировка, чтобы пагинация была стабильной
            .limit(PAGE_SIZE)
            .offset(offset)
        )
        items = result.scalars().all()

        # Определяем, есть ли следующая страница
        result_count = await session.execute(
            select(UserItem.id)
            .join(User, User.id == UserItem.user_id)
            .where(User.tg_id == tg_id)
        )
        total_items = result_count.scalars().all()
        total_pages = (len(total_items) + PAGE_SIZE - 1) // PAGE_SIZE

    return items, total_pages

async def get_user_item_by_id(id: int):
    async with async_session() as session:
        date = await session.execute(select(UserItem).where(UserItem.id == id))
        return date.scalars().first()

async def delete_date_by_id(id: int):
    async with async_session() as session:
        await session.execute(
            delete(UserItem).where(UserItem.id == id)
        )
        await session.commit()