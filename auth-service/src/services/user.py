from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.models.user import User, OAuthAccount, Provider
from src.services.token import hash_token
import hashlib


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    """Получение пользователя по email"""
    result = await session.execute(
        select(User).where(User.email == email)
    )
    return result.scalar_one_or_none()


async def get_user_by_id(session: AsyncSession, user_id: str) -> User | None:
    """Получение пользователя по ID"""
    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    return result.scalar_one_or_none()


async def create_user(
    session: AsyncSession,
    email: str,
    password_hash: str,
    name: str,
) -> User:
    """Создание нового пользователя"""
    user = User(
        email=email,
        password_hash=password_hash,
        name=name,
    )
    session.add(user)
    await session.flush()
    await session.refresh(user)
    return user


async def create_oauth_account(
    session: AsyncSession,
    user_id: str,
    provider: Provider,
    provider_id: str,
    access_token: str | None = None,
) -> OAuthAccount:
    """Создание OAuth аккаунта"""
    oauth_account = OAuthAccount(
        user_id=user_id,
        provider=provider,
        provider_id=provider_id,
        access_token=access_token,
    )
    session.add(oauth_account)
    await session.flush()
    await session.refresh(oauth_account)
    return oauth_account


async def get_oauth_account(
    session: AsyncSession, provider: Provider, provider_id: str
) -> OAuthAccount | None:
    """Получение OAuth аккаунта по провайдеру и ID"""
    result = await session.execute(
        select(OAuthAccount).where(
            OAuthAccount.provider == provider,
            OAuthAccount.provider_id == provider_id,
        )
    )
    return result.scalar_one_or_none()


async def find_or_create_oauth_user(
    session: AsyncSession,
    provider: Provider,
    provider_id: str,
    email: str,
    name: str,
    avatar_url: str | None = None,
) -> User:
    """Найти или создать пользователя по OAuth профилю"""
    # Проверяем существующий OAuth аккаунт
    oauth_account = await get_oauth_account(session, provider, provider_id)

    if oauth_account:
        # Пользователь уже существует
        result = await session.execute(
            select(User).where(User.id == oauth_account.user_id)
        )
        return result.scalar_one_or_none()

    # Проверяем существующего пользователя по email
    user = await get_user_by_email(session, email)

    if user:
        # Привязываем OAuth аккаунт к существующему пользователю
        await create_oauth_account(
            session, str(user.id), provider, provider_id
        )
        return user

    # Создаём нового пользователя
    user = User(
        email=email,
        password_hash=None,  # OAuth пользователи не имеют пароля
        name=name,
        avatar_url=avatar_url,
    )
    session.add(user)
    await session.flush()

    # Создаём OAuth аккаунт
    await create_oauth_account(
        session, str(user.id), provider, provider_id
    )

    return user
