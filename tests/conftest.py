"""Make the test suite independent from developer-local .env files."""
import os


os.environ["APP_MODE"] = "dev"
