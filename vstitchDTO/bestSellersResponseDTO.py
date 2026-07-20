from typing import List, Literal

from pydantic import BaseModel

from vstitchDTO.productCardResponseDTO import ProductCardResponseDTO


class BestSellerItemDTO(ProductCardResponseDTO):
    # "sales": ranked by real order history (recent or all-time). "fallback":
    # padding from newest-active products, used only when there isn't enough
    # sales data yet - never mixed together unlabeled, see BestSellerService.
    source: Literal["sales", "fallback"]


class BestSellersResponseDTO(BaseModel):
    items: List[BestSellerItemDTO]
    # How many of `items` have source == "sales" - lets the frontend decide
    # whether to show/relabel/hide the section on a catalog with thin sales
    # history, instead of silently presenting fallback padding as bestsellers.
    qualifying_count: int
