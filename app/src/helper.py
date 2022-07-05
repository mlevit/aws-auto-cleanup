import datetime
import fnmatch

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

    # https://codereview.stackexchange.com/a/253174/234246
    @staticmethod
    def get_setting(settings, path, default=None):
        result = settings
        for key in path.split("."):
            result = result.get(key)
            if result is None:
                return default
        return result

    @staticmethod
    def get_allowlist(allowlist, path, default=None):
        result = allowlist
        for key in path.split("."):
            result = result.get(key)
            if result is None:
                return default or []
        return result

    @staticmethod
    def not_allowlisted(resource_id, allowlist):
        if not any(fnmatch.fnmatch(resource_id, pattern) for pattern in allowlist):
            return True
        else:
            return False

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
        execution_log, region, service, resource, resource_id, resource_action
    ):
        execution_log["AWS"][region][service][resource].append(
            {
                "id": resource_id,
                "action": resource_action,
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
