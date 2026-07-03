import json
from decimal import Decimal


class DecimalEncoder(json.JSONEncoder):
    """
    JSON encoder that converts DynamoDB Decimal values to int or float.

    DynamoDB returns numeric attributes as Decimal via boto3's resource API.
    The default json.dumps() cannot serialize Decimal, so this encoder
    converts whole-number Decimals to int and fractional ones to float.
    """

    def default(self, obj):
        if isinstance(obj, Decimal):
            if obj % 1 == 0:
                return int(obj)
            return float(obj)
        return super().default(obj)
