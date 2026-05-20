import sqlite3
import os
import sys
from pathlib import Path

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
            temp_con.execute("PRAGMA foreign_keys = ON") # necessary it seems from docs 
            temp_con.execute(TASKS_SCHEMA_CREATE_QUERY)
            #temp_con.execute(TASKS_RELATIONS_SCHEMA_CREATE_QUERY)
            temp_con.execute(TASKS_TIMESTAMPS_SCHEMA_CREATE_QUERY)
            temp_con.commit()

    def __enter__(self):
        self._active_con = sqlite3.connect(self.db_file)
        self.cur = self._active_con.cursor()
    
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

    def create_task(self, task_args):

        # keep these queries in or outside this? 
        TASK_INSERT_QUERY = """
        INSERT INTO Tasks
        (id, name, description, target_start_time, target_time, created_time, dead_time, is_complete, priority)
        VALUES
        (?,?,?,?,?,?,?,?,?);
        """
        self.cur.executemany(TASK_INSERT_QUERY, task_args)

    def delete_task_by_id(self, task_id):

        TASK_DELETE_QUERY = """
        DELETE FROM Tasks
        WHERE id = ? ;
        """
        self.cur.executemany(TASK_DELETE_QUERY, task_id)

    def fetch_task(self, task_id):
        
        TASK_VIEW_QUERY = """
        SELECT * FROM Tasks
        WHERE id = ?;
        """
        res = self.cur.execute(TASK_VIEW_QUERY, task_id)
        return res.fetchall()
    
    def modify_task(self, task_id, task_param, task_arg):

        TASK_MODIFY_QUERY = """
        UPDATE Tasks
        SET ? = ?
        WHERE id = ?
        """
        self.cur.execute(TASK_MODIFY_QUERY, (task_param, task_arg, task_id) ) 

    def task_event_entry(self, task_id, event_type, timestamp):

        TASK_EVENT_ENTRY_QUERY = """
        INSERT INTO TasksTimestamps
        (task_id, event_type, timestamp)
        VALUES
        (?,?,?);
        """
        self.cur.execute(TASK_EVENT_ENTRY_QUERY, (task_id, event_type, timestamp))

    def delete_database(self):

        DELETE_DATABASE_QUERY = """
        DROP TABLE IF EXISTS TasksRelations, TasksTimestamps, Tasks;
        """

        self.cur.execute(DELETE_DATABASE_QUERY)



### TESTING CODE <><><>
if __name__ == "__main__":
    task_params = [( "ab32", "attain nuclear fission" , "use thorium" , "5:30 am ust", "NEIN", "NEIN" , "NEIN" , True, 0 )]
    # seems executemany() likes a proper list. sending a 1D tuple breaks it (thinks ab32 is a tuple within it and iterates through it).
    db = DatabaseManager()
    task_id = ("ab32",)

    with db: # if want "as" , use __enter__ with return self statement... pythonic much? 
        db.fetch_task(task_id)
