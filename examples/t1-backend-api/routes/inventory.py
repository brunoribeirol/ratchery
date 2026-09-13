from fastapi import APIRouter

router = APIRouter(prefix="/inventory")

_STOCK: dict[str, int] = {"widget-a": 42, "widget-b": 7}


@router.get("/{sku}")
def get_stock(sku: str) -> dict[str, int | str]:
    return {"sku": sku, "count": _STOCK.get(sku, 0)}


@router.post("/{sku}/adjust")
def adjust_stock(sku: str, delta: int) -> dict[str, int | str]:
    _STOCK[sku] = _STOCK.get(sku, 0) + delta
    return {"sku": sku, "count": _STOCK[sku]}
