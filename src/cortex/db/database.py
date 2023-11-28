from pathlib import Path

import sqlalchemy

from cortex import consts
from cortex.db.tables import Base

Path(consts.storage_folder).mkdir(parents=True, exist_ok=True)
engine = sqlalchemy.create_engine(f"sqlite:///{consts.storage_folder}/{consts.database_file}")
Base.metadata.create_all(engine)
