#!/usr/bin/env python3

import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from modules.database import Database

db = Database()
db.purge()
db.close()
