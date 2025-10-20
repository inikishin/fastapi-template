BOND_FIELD_MAPPING = {
    "SECID": "code",
    "SHORTNAME": "name",
    "SECNAME": "description",
    "COUPONVALUE": "coupon_value",
    "COUPONPERCENT": "coupon_percent",
    "NEXTCOUPON": "coupon_next_date",
    "COUPONPERIOD": "coupon_period",
    "ACCRUEDINT": "accrued_income",
    "PREVPRICE": "prev_price",
    "PREVDATE": "prev_date",
    "LOTSIZE": "lot_size",
    "FACEVALUE": "face_value",
    "MATDATE": "due_date",
    "DECIMALS": "decimals",
    "ISSUESIZE": "issue_size",
    "ISIN": "isin",
    "REGNUMBER": "reg_number",
}

BOND_COUPON_SCHEDULE_FIELD_MAPPING = {
    "startdate": "start_date",
    "recorddate": "record_date",
    "coupondate": "coupon_date",
    "value": "value",
    "valueprc": "value_percent",
}
