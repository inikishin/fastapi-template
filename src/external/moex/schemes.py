from datetime import date

from pydantic import BaseModel

class BondSchema(BaseModel):
    code: str | None = None
    name: str | None = None
    description: str | None = None
    type: str | None = None
    group: str | None = None
    list_level: str | None = None
    status: str | None = None
    coupon_value: float | None = None
    coupon_percent: float | None = None
    coupon_next_date: str | None = None
    coupon_period: int | None = None
    accrued_income: float | None = None
    prev_price: float | None = None
    prev_date: str | None = None
    lot_size: float | None = None
    face_value: float | None = None
    due_date: str | None = None
    decimals: float | None = None
    isin: str | None = None
    reg_number: str | None = None
    currency: str | None = None
    is_for_qualified_investors: bool | None = None


class BondCouponScheduleSchema(BaseModel):
    start_date: str
    record_date: str
    coupon_date: str
    value: float
    value_percent: float
