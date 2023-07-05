from db.db_operations import AdminDB, ObjectFactory


async def i_set_theme(
    user_theme: str, admin_unit: AdminDB, chat_id: int, time: int = 604800
):
    theme = ObjectFactory.build_theme_fsm(user_theme)
    msg = await admin_unit.set_contest_theme(chat_id, theme, time) + " - новая тема"
    return msg
