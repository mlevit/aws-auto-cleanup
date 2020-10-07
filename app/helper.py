import datetime

import dateutil.parser


class Helper:
    def __init__(self):
        pass

    @staticmethod
    def convert_to_datetime(date):
        return dateutil.parser.isoparse(str(date)).replace(tzinfo=None)

    @staticmethod
    def get_day_delta(resource_date):
        if resource_date is not None:
            from_datetime = Helper.convert_to_datetime(
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            to_datetime = Helper.convert_to_datetime(resource_date)
            return from_datetime - to_datetime
        else:
            return 0

    @staticmethod
    def parse_resource_id(resource_id):
        elements = resource_id.split(":", 2)

        result = {
            "service": elements[0],
            "resource_type": elements[1],
            "resource": elements[2],
        }

        return result

    @staticmethod
    def _unmarshal_value(node):
        if type(node) is not dict:
            return node

        for key, value in node.items():
            # S – String - return string
            # N – Number - return int or float (if includes '.')
            # B – Binary - not handled
            # BOOL – Boolean - return Bool
            # NULL – Null - return None
            # M – Map - return a dict
            # L – List - return a list
            # SS – String Set - not handled
            # NN – Number Set - not handled
            # BB – Binary Set - not handled
            key = key.lower()
            if key == "bool":
                return value
            if key == "null":
                return None
            if key == "s":
                return value
            if key == "n":
                if "." in str(value):
                    return float(value)
                return int(value)
            if key in ["m", "l"]:
                if key == "m":
                    data = {}
                    for key1, value1 in value.items():
                        if key1.lower() == "l":
                            data = [Helper._unmarshal_value(n) for n in value1]
                        else:
                            if type(value1) is not dict:
                                return Helper._unmarshal_value(value)
                            data[key1] = Helper._unmarshal_value(value1)
                    return data
                data = []
                for item in value:
                    data.append(Helper._unmarshal_value(item))
                return data

    @staticmethod
    def unmarshal_dynamodb_json(node):
        data = dict({})
        data["M"] = node
        return Helper._unmarshal_value(data)