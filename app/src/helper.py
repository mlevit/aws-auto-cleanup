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
        from_datetime = Helper.convert_to_datetime(
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

        if resource_date is not None:
            to_datetime = Helper.convert_to_datetime(resource_date)
            return from_datetime - to_datetime
        else:
            return from_datetime - from_datetime

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
    def record_execution_log_action(
        execution_log, region, service, resource, id, action
    ):
        execution_log.get("AWS").setdefault(region, {}).setdefault(
            service, {}
        ).setdefault(resource, []).append(
            {
                "id": id,
                "action": action,
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
