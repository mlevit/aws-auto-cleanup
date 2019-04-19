import boto3
import datetime
import dateutil.parser
import os

class Helper:
    def __init__(self):
        pass
    
    
    @staticmethod
    def convert_to_datetime(date):
        return dateutil.parser.isoparse(date).replace(tzinfo=None)
    
    
    @staticmethod
    def get_day_delta(resource_date):
        if resource_date is not None:
            from_datetime = Helper.convert_to_datetime(str(datetime.datetime.now().isoformat()))
            to_datetime = Helper.convert_to_datetime(str(resource_date))
            return from_datetime - to_datetime
        else:
            return 0
    
    
    @staticmethod
    def parse_arn(arn):
        elements = arn.split(':', 5)
        result = {
            'arn': elements[0],
            'partition': elements[1],
            'service': elements[2],
            'region': elements[3],
            'account': elements[4],
            'resource': elements[5],
            'resource_type': None}
        
        if '/' in result['resource']:
            result['resource_type'], result['resource'] = result['resource'].split('/',1)
        elif ':' in result['resource']:
            result['resource_type'], result['resource'] = result['resource'].split(':',1)
        return result
    
    
    @staticmethod
    def parse_resource_id(resource_id):
        elements = resource_id.split(':', 2)
        
        result = {
            'service': elements[0],
            'resource_type': elements[1],
            'resource': elements[2]}

        return result

