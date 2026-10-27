def details(user):
    """
    The signed-in user as Deacon is told them, found the same way for the page and for the token
    route: the id as a string, and the email and name, or None for one the user hasn't got. None
    when the user names nobody: AnonymousUser, or a user with no id, such as one never saved.
    """
    if not user.is_authenticated or user.pk is None or str(user.pk) == "":
        return None

    email_field = user.get_email_field_name() if hasattr(user, "get_email_field_name") else "email"
    email = getattr(user, email_field, None)
    get_full_name = getattr(user, "get_full_name", None)
    name = get_full_name() if callable(get_full_name) else None

    return {"id": str(user.pk), "email": email or None, "name": name or None}
