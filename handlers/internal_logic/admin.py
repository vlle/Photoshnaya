from db.db_operations import ObjectFactory, AdminDB

async def i_set_theme(user_theme: str,
                admin_unit: AdminDB, chat_id: int):
    theme = ObjectFactory.build_theme_fsm(user_theme)
    time = 604800
    msg = await admin_unit.set_contest_theme(chat_id,
                                           theme, time) + " - новая тема"
    return msg
