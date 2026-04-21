"""
appwrite_client.py
Appwrite client singleton — import `databases` from here everywhere.
"""

import os
from appwrite.client import Client
from appwrite.services.databases import Databases
from dotenv import load_dotenv

load_dotenv()

_client = Client()
_client.set_endpoint(os.environ["APPWRITE_ENDPOINT"])
_client.set_project(os.environ["APPWRITE_PROJECT_ID"])
_client.set_key(os.environ["APPWRITE_API_KEY"])

databases = Databases(_client)