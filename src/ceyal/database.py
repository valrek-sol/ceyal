import sqlite3
import os
import sys
from pathlib import Path
from .custom_types import TaskRow, TimestampRow, TaskRelationsRow

APP_NAME = "ceyal"

def get_default_db_path():
    if sys.platform.startswith("linux"):
        data_home = os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")
    elif sys.platform == "darwin":
        data_home = Path.home() / "Library" / "Application Support"
    elif sys.platform.startswith("win"):
        data_home = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        data_home = Path.home()
    
    app_data_dir = Path(data_home) / APP_NAME
    app_data_dir.mkdir(parents=True, exist_ok=True)
    return app_data_dir/"ceyal.db"

DB_FILE_PATH_DEFAULT = get_default_db_path()

ALLOWED_MODIFIABLE_PARAMS = {"name", "description", "target_start_time", "target_time", "created_time", "dead_time", "is_complete", "priority" }

# Tasks Schema
TASKS_SCHEMA_CREATE_QUERY = """
CREATE TABLE IF NOT EXISTS Tasks
(
    id                  TEXT PRIMARY KEY        ,
    name                TEXT                    ,
    description          TEXT                    ,
    target_start_time   TEXT                    ,
    target_time         TEXT                    ,
    created_time        TEXT                    ,
    dead_time           TEXT                    ,
    is_complete         BOOLEAN     DEFAULT 0   ,
    priority            INTEGER                 
);
"""

# Tasks relations schema (to be utilized for DAG)

TASKS_RELATIONS_SCHEMA_CREATE_QUERY = """
CREATE TABLE IF NOT EXISTS TasksRelations
(
    super_task_id       TEXT                    ,
    sub_task_id         TEXT                    ,
    PRIMARY KEY (super_task_id,sub_task_id)     ,
    FOREIGN KEY (super_task_id)     REFERENCES Tasks(id)    ,
    FOREIGN KEY (sub_task_id)       REFERENCES Tasks(id)    
);
"""

#Tasks timestamps schema

TASKS_TIMESTAMPS_SCHEMA_CREATE_QUERY = """
CREATE TABLE IF NOT EXISTS TasksTimestamps
(
    event_id            INTEGER PRIMARY KEY AUTOINCREMENT   ,
    task_id             TEXT                    ,
    event_type          TEXT                    ,
    timestamp           TEXT                    ,
    FOREIGN KEY (task_id) REFERENCES Tasks(id) ON DELETE CASCADE
);
"""

#chitti give me your neural schema

class DatabaseManager:
    def __init__(self,db_file=DB_FILE_PATH_DEFAULT):
        self._active_con = None
        self.db_file = db_file
        self._initialize_tables()

    def _initialize_tables(self):
        with sqlite3.connect(self.db_file) as temp_con:
            # necessary it seems from docs , not sure if temp also needs it 
            temp_con.execute("PRAGMA foreign_keys = ON") 
            temp_con.execute(TASKS_SCHEMA_CREATE_QUERY)
            #temp_con.execute(TASKS_RELATIONS_SCHEMA_CREATE_QUERY)
            temp_con.execute(TASKS_TIMESTAMPS_SCHEMA_CREATE_QUERY)
            temp_con.commit()

    def __enter__(self):
        self._active_con = sqlite3.connect(self.db_file)
        self._active_con.execute("PRAGMA foreign_keys = ON")
        self.cur = self._active_con.cursor()

        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self._active_con:
            return False
        try:
            if exc_type is not None: #this means error happened it seems
                self._active_con.rollback()
            else:
                self._active_con.commit()
        finally:
            self._active_con.close()
            self._active_con = None

    def create_task(self, task: list[TaskRow]): 
        """
        Add a batch of tasks or a single task to the Tasks table.

        Args:
            task: list of namedtuples[TaskRow]/tuples all parameters of a task.
        """

        # keep these queries in or outside this? 
        TASK_INSERT_QUERY = """
        INSERT INTO Tasks
        (id, name, description, target_start_time, target_time, created_time, dead_time, is_complete, priority)
        VALUES
        (?,?,?,?,?,?,?,?,?);
        """

        self.cur.executemany(TASK_INSERT_QUERY, task)

    def delete_task_by_id(self, task_ids: list[tuple[str]]):
        """
        Delete a task, or a bunch of tasks using their ids.

        Args:
            task_ids: list of tuple containing the id of the task ; 
                hex in the form of a string. 
                Examples : [("ab32bf66...",),("afee88...",)]
        """

        TASK_DELETE_QUERY = """
        DELETE FROM Tasks
        WHERE id = ? ;
        """
        self.cur.executemany(TASK_DELETE_QUERY, task_ids)

    def fetch_task_by_id(self, task_ids: list[tuple[str]]) -> list[TaskRow]:
        """
        Fetch a task, or a bunch of tasks using their ids.

        Args:
            task_ids: list of tuple containing the id of the task ; 
                hex in the form of a string.
                Examples : [("ab32bf66...",),("afee88...",)]
        Returns:
            A list of TaskRow namedtuples with the parameters of the task.
        """
 
        placeholder = ",".join("?"*len(task_ids))
        TASK_VIEW_QUERY = f"""
        SELECT * FROM Tasks
        WHERE id IN ({placeholder}) ;
        """
        res = self.cur.execute(TASK_VIEW_QUERY, [tid for (tid,) in task_ids])
        return [TaskRow(*row) for row in res.fetchall()]

    def fetch_task_by_partial_id(self, partial_id: str) -> TaskRow:
        """
        Fetch a task using the incomplete id.

        Args:
            partial_id: string containing the incomplete id of the task  
                Examples : ("ab32",)
        Returns:
            A TaskRow namedtuple with the parameters of the task.
        """
 
        TASK_VIEW_QUERY_SPL = f"""
        SELECT * FROM Tasks
        WHERE id LIKE ? ;
        """
        res = self.cur.execute(TASK_VIEW_QUERY_SPL, (f"{partial_id}%",)) 
        return TaskRow(*(res.fetchone()))


    def fetch_all_tasks(self, num_rows = None): 
        """
        Fetch all task details.

        Args:
            num_rows : number of rows to return. -1 for full list.

        Returns:
            Full list of TaskRow namedtuples with the parameters of the task
                from database.
        """

        if num_rows:
            res = self.cur.execute("SELECT * FROM Tasks LIMIT ?", (num_rows,))
        else:
            res = self.cur.execute("SELECT * FROM Tasks")
        return [TaskRow(*row) for row in res.fetchall()]
    
    def modify_task(self, task_ids: list[tuple[str]], task_update_values: list[tuple]):
        """
        Modify task (same set of) parameter values for single or multiple task_ids.

        Args:
            task_ids: list of tuple containing the id of the task ; 
                hex in the form of a string.
                Examples : [("ab32bf66...",),("afee88...",)]
            task_update_values: contain [(parameter to be modified, parameter value),...] 
        """

        for (task_param,task_arg_new) in task_update_values:
            if task_param not in ALLOWED_MODIFIABLE_PARAMS:
                raise ValueError(f"[DATABASE] PARAMETER {task_param} is NOT ALLOWED TO BE MODIFIED")
            TASK_MODIFY_QUERY = f"""
            UPDATE Tasks
            SET {task_param} = ?
            WHERE id = ? ;
            """
            self.cur.executemany(TASK_MODIFY_QUERY, [(task_arg_new, tid) for (tid,) in task_ids] ) 

    def task_event_entry(self, task_ids: list[tuple[str]], event_type: str, timestamp: str):
        """
        Registers a event (start/pause/resume/complete) in the database for a task or multiple tasks.

        Args:
            task_ids: list of tuple containing the id of the task ; 
                hex in the form of a string.
                Examples : [("ab32bf66...",),("afee88...",)]
            event_type: start/pause/resume/complete
            timestamp: datetime in string.
        """

        TASK_EVENT_ENTRY_QUERY = """
        INSERT INTO TasksTimestamps
        (task_id, event_type, timestamp)
        VALUES
        (?,?,?);
        """
        self.cur.executemany(TASK_EVENT_ENTRY_QUERY, [(tid, event_type, timestamp) for (tid,) in task_ids])

    def fetch_task_events(self, task_ids: list[tuple[str]]):
        """
        Fetches events for the task_id given.

        Args:
            task_ids: list of tuple containing the id of the task ; 
                hex in the form of a string.
                Examples : [("ab32bf66...",),("afee88...",)]
        """

        placeholder = ",".join("?"*len(task_ids))
        TASK_VIEW_EVENTS_QUERY = f"""
        SELECT * FROM TasksTimestamps
        WHERE task_id IN ({placeholder})
        ORDER BY timestamp;
        """
        res = self.cur.execute(TASK_VIEW_EVENTS_QUERY,[tid for (tid,) in task_ids])
        return [TimestampRow(*row) for row in res.fetchall()]

    def fetch_all_tasks_events(self):
        """
        Fetches events for all task_ids there is.
        """
        
        TASKS_VIEW_ALL_EVENTS_QUERY = """
        SELECT * FROM TasksTimestamps
        ORDER BY timestamp;
        """
        res = self.cur.execute(TASKS_VIEW_ALL_EVENTS_QUERY)
        return [TimestampRow(*row) for row in res.fetchall()]

    def delete_database(self):
        """
        Use with caution. Deletes the entire database along with the schema.
        """

        self.cur.execute("DROP TABLE IF EXISTS TasksRelations;")
        self.cur.execute("DROP TABLE IF EXISTS TasksTimestamps;")
        self.cur.execute("DROP TABLE IF EXISTS Tasks;")
