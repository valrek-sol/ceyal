from collections import namedtuple

task_parameters = ["id","name","description","target_start_time",
                   "target_time","created_time","dead_time",
                   "is_complete","priority"]
TaskRow = namedtuple("TaskRow", task_parameters)

timestamp_parameters = ["event_id","task_id","event_type","timestamp"]
TimestampRow = namedtuple("TimestampRow", timestamp_parameters)

task_relations_parameters = ["super_task_id","sub_task_id"]
TaskRelationsRow = namedtuple("TaskRelationsRow",task_relations_parameters)
