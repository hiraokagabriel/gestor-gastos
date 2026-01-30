from datetime import datetime
from calendar import monthrange

from sqlalchemy import extract

from database import db
from models import Account


def ensure_recurring_materialized_for_month(year: int, month: int) -> int:
    """Garante que cada origem recorrente tenha uma instância (filho) para o mês/ano informados.

    Regra:
    - Não gera meses anteriores ao mês/ano de início (date) da origem.
    - Se a origem já pertence ao mês/ano alvo, não cria filho (a origem é o lançamento daquele mês).
    - Evita duplicidade checando por parent_id + (year, month).

    Retorna a quantidade de lançamentos criados.
    """
    origins = Account.query.filter(
        Account.recurring == True,
        Account.parent_id.is_(None)
    ).all()

    created = 0
    for origin in origins:
        if not origin.date:
            continue

        origin_ym = (origin.date.year, origin.date.month)
        target_ym = (year, month)

        # Não gerar para meses anteriores ao início da origem
        if target_ym < origin_ym:
            continue

        # Se a própria origem já é do mês/ano alvo, não cria filho
        if origin.date.year == year and origin.date.month == month:
            continue

        day = origin.recurring_day or origin.date.day
        max_day = monthrange(year, month)[1]
        day = min(day, max_day)
        target_date = datetime(year, month, day)

        exists = Account.query.filter(
            Account.parent_id == origin.id,
            extract('year', Account.date) == year,
            extract('month', Account.date) == month
        ).first()

        if exists:
            continue

        child = Account(
            description=origin.description,
            amount=origin.amount,
            type=origin.type,
            category=origin.category,
            date=target_date,
            recurring=False,
            parent_id=origin.id,
            recurring_day=origin.recurring_day,
            consolidated=False
        )
        db.session.add(child)
        created += 1

    if created:
        db.session.commit()

    return created


def list_recurring_occurrences_for_month(year: int, month: int, account_type: str) -> list[dict]:
    """Lista as ocorrências recorrentes do mês (uma por origem), sem ambiguidade.

    Convenção:
    - Se a origem cair no mês alvo, ela mesma é a ocorrência (source='origin').
    - Caso contrário, a ocorrência é o filho materializado (source='child').

    A função sempre materializa o mês primeiro para evitar "sumir" recorrências.
    """
    ensure_recurring_materialized_for_month(year, month)

    origins = Account.query.filter(
        Account.type == account_type,
        Account.recurring == True,
        Account.parent_id.is_(None)
    ).all()

    items: list[dict] = []
    for origin in origins:
        if not origin.date:
            continue

        origin_ym = (origin.date.year, origin.date.month)
        target_ym = (year, month)
        if target_ym < origin_ym:
            continue

        if origin.date.year == year and origin.date.month == month:
            acc = origin
            source = 'origin'
        else:
            acc = Account.query.filter(
                Account.parent_id == origin.id,
                extract('year', Account.date) == year,
                extract('month', Account.date) == month
            ).first()
            source = 'child' if acc else 'missing'

        if not acc:
            # Não deveria acontecer se materialização estiver ok
            continue

        items.append({
            'source': source,
            'origin_id': origin.id,
            'account_id': acc.id,
            'description': acc.description,
            'amount': float(acc.amount),
            'date': acc.date.strftime('%d/%m/%Y') if acc.date else None,
        })

    return items
