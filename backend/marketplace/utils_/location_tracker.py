import json
import logging

from redis import Redis


class LocationTracker:

    def __init__(self):
        self.redis: Redis = Redis(host='redis', port=6379)

    def set_location(self, courier_id: str, location: dict[str, str]):
        self.redis.set(courier_id, json.dumps(location))

    def get_location(self, courier_id: str) -> dict[str, str] | None:
        try:
            location = self.redis.get(courier_id)
            return json.loads(location)
        except TypeError as e:
            logging.error(f'Could not fetch courier location {e}')
            return

    def get_all_locations(self) -> dict[int, dict[str, str]]:
        pattern = "?????????"
        cursor, keys = self.redis.scan(match=pattern)
        cursor2, keys2 = self.redis.scan(match=pattern + '?')
        result = {}
        for key in keys + keys2:
            location = self.get_location(key)
            result[int(key)] = location
        return result
