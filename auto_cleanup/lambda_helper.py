import datetime

import dateutil.parser


class LambdaHelper:
    def __init__(self):
        pass

    @staticmethod
    def convert_to_datetime(date):
        return dateutil.parser.isoparse(str(date)).replace(tzinfo=None)

    @staticmethod
    def get_day_delta(resource_date):
        if resource_date is not None:
            from_datetime = LambdaHelper.convert_to_datetime(
                datetime.datetime.now().isoformat()
            )
            to_datetime = LambdaHelper.convert_to_datetime(resource_date)
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
