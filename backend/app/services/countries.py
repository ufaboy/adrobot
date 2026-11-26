from functools import cache

import pycountry

from app.schemas.reference import Country


@cache
def list_countries() -> tuple[Country, ...]:
    """ISO 3166-1 countries sorted by name."""
    countries = (Country(code=c.alpha_2, name=c.name) for c in pycountry.countries)
    return tuple(sorted(countries, key=lambda c: c.name))


@cache
def _codes() -> frozenset[str]:
    return frozenset(c.code for c in list_countries())


def is_country_code(code: str) -> bool:
    return code in _codes()
