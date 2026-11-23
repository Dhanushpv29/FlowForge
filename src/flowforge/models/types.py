import enum

from sqlalchemy import Enum


def status_enum(enum_cls: type[enum.Enum], name: str, length: int) -> Enum:
    """Store the enum *value* in a VARCHAR guarded by a named CHECK constraint.

    Non-native enums avoid ALTER TYPE pain in migrations while the CHECK still
    stops invalid states at the database level.
    """
    return Enum(
        enum_cls,
        name=name,
        length=length,
        native_enum=False,
        create_constraint=True,
        validate_strings=True,
        values_callable=lambda e: [member.value for member in e],
    )
