from aiogram import Router

from .common import router as common_router
from .quotes import router as quotes_router
from .activists import router as activists_router
from .games import router as games_router
from .math_duel import router as math_duel_router
from .reminders import router as reminders_router
from .fun import router as fun_router
from .help import router as help_router

# Главный роутер, объединяющий все остальные
main_router = Router(name="main")
main_router.include_router(common_router)
main_router.include_router(help_router)
main_router.include_router(quotes_router)
main_router.include_router(activists_router)
main_router.include_router(games_router)
main_router.include_router(math_duel_router)
main_router.include_router(reminders_router)
main_router.include_router(fun_router)

__all__ = ["main_router"]
