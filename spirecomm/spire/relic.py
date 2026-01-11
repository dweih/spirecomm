class Relic:

    def __init__(self, relic_id, name, counter=0, price=0):
        self.relic_id = relic_id
        self.name = name
        self.counter = counter
        self.price = price

    @classmethod
    def from_json(cls, json_object):
        return cls(json_object["id"], json_object["name"], json_object["counter"], json_object.get("price", 0))

    def to_json(self):
        """Serialize Relic to JSON-compatible dict"""
        return {
            'id': self.relic_id,
            'name': self.name,
            'counter': self.counter,
            'price': self.price
        }
