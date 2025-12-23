from fastapi import APIRouter

from app.api.routes import auth, cart, catalog, config, orders, stock, users

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(catalog.router)
api_router.include_router(cart.router)
api_router.include_router(orders.router)
api_router.include_router(stock.router)
api_router.include_router(config.router)
