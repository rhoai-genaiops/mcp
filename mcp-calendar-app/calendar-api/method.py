import configparser
import json
import datetime

class Method:
    def __init__(self, conf_file):
        self.config = configparser.ConfigParser()
        self.config.read(conf_file)
        self.info = self.config['DEFAULT']
        self.columns = json.loads(self.info['columns'])

    def check_params(self, jsn):
        # Accept priority levels 1, 2, 3 (Low, Medium, High)
        if jsn['level'] not in [1, 2, 3]:
            return False
        if not (0 <= jsn['status'] <= 1):
            return False
        try:
            for t in ['creation_time', 'start_time', 'end_time']:
                datetime.datetime.strptime(jsn[t], '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return False
        return True

    def get(self, dbh, schedule_id, user_id=None):
        condition = {'sid': schedule_id}
        if user_id:
            condition['user_id'] = user_id
        return dbh.fetch_data(
            table_name=self.info['table_name'],
            condition=condition)

    def post(self, dbh, schedule, user_id=None):
        schedule_dict = schedule.dict()
        # If user_id is provided, ensure it's set in the schedule
        if user_id:
            schedule_dict['user_id'] = user_id

        condition = {'sid': schedule.sid}
        if user_id:
            condition['user_id'] = user_id

        if dbh.check_existence(self.info['table_name'], condition):
            return False
        if not self.check_params(schedule_dict):
            return False
        dbh.insert_data(self.info['table_name'], self.columns, schedule_dict)
        return True

    def update(self, dbh, schedule_id, schedule, user_id=None):
        schedule_dict = schedule.dict()
        # If user_id is provided, ensure it's set in the schedule
        if user_id:
            schedule_dict['user_id'] = user_id

        condition = {'sid': schedule_id}
        if user_id:
            condition['user_id'] = user_id

        if not dbh.check_existence(self.info['table_name'], condition):
            return False
        if not self.check_params(schedule_dict):
            return False
        dbh.update_data(self.info['table_name'], schedule_dict, condition)
        return True

    def delete(self, dbh, schedule_id, user_id=None):
        condition = {'sid': schedule_id}
        if user_id:
            condition['user_id'] = user_id

        if not dbh.check_existence(self.info['table_name'], condition):
            return False
        dbh.delete_data(self.info['table_name'], condition)
        return True

if __name__ == '__main__':
    m = Method(conf_file='db.conf')
