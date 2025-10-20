import httpx

from src.config.logger import LoggerProvider
from src.external.moex.constants import BOND_FIELD_MAPPING, \
    BOND_COUPON_SCHEDULE_FIELD_MAPPING
from src.external.moex.schemes import BondSchema, BondCouponScheduleSchema

logger = LoggerProvider().get_logger("src.external.moex.moex")


class Moex:
    def __init__(self, silence: bool = True):
        self.base_url = "https://iss.moex.com/iss/"
        self.silence = silence

    async def _get_request(self, url: str, query_params: dict = None) -> tuple[int, dict]:
        async with httpx.AsyncClient() as client:
            url = self.base_url + url
            if not self.silence:
                logger.info(
                    "GET request to %s with params: %s",
                    url,
                    query_params,
                )
            response = await client.get(url, params=query_params)
            if not self.silence:
                logger.info(
                    "response from %s with status code %s.\nResponse body:\n%s",
                    url,
                    response.status_code,
                    response.text,
                )
        return response.status_code, response.json()

    def _data_as_dict(self, response_data: dict, target: str) -> list:
        data = []
        columns = response_data.get(target).get("columns")
        for row in response_data.get(target).get("data"):
            item_data = {}
            for index, row_value in enumerate(row):
                item_data[columns[index]] = row_value
            data.append(item_data)

        return data

    async def get_bonds(self, query_params: dict = None) -> list[BondSchema]:
        status, response = await self._get_request(
            "engines/stock/markets/bonds/securities.json",
            query_params={
                "marketprice_board": "1",
            }
        )

        if status != 200:
            raise Exception(f"Error getting bonds: {status} {response}")
        result = []
        for item in self._data_as_dict(response, "securities"):
            data = {}
            for key, value in BOND_FIELD_MAPPING.items():
                data[value] = item.get(key)
            result.append(BondSchema(**data))
        return result

    def get_bond_by_id(self, bond_id: str) -> dict:
        return {}

    async def get_bond_schedule(self, bond_code: str) -> list[BondCouponScheduleSchema]:
        url = f"securities/{bond_code}/bondization.json"
        status, response = await self._get_request(
            url,
            query_params={
                "iss.only": "coupons",
                "limit": "unlimited",
            }
        )

        if status != 200:
            raise Exception(f"Error getting bonds schedule: {status} {response}")

        result = []
        for item in self._data_as_dict(response, "coupons"):
            data = {}
            for key, value in BOND_COUPON_SCHEDULE_FIELD_MAPPING.items():
                data[value] = item.get(key)
            result.append(BondCouponScheduleSchema(**data))

        return result



async def main():
    m = Moex(silence=False)
    r = await m.get_bonds()
    r1 = await m.get_bond_schedule(r[0].code)
    print(r1)

import asyncio
asyncio.run(main())