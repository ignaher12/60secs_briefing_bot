import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    anthropic_api_key: str
    bright_data_token: str
    bright_data_serp_zone: str
    bright_data_unlocker_zone: str
    bright_data_browser_ws: str
    db_path: str
    bright_data_call_cap: int


def load_config() -> Config:
    return Config(
        anthropic_api_key=os.environ["ANTHROPIC_API_KEY"],
        bright_data_token=os.environ["BRIGHT_DATA_API_TOKEN"],
        bright_data_serp_zone=os.environ["BRIGHT_DATA_SERP_ZONE"],
        bright_data_unlocker_zone=os.environ["BRIGHT_DATA_UNLOCKER_ZONE"],
        bright_data_browser_ws=os.environ["BRIGHT_DATA_BROWSER_WS"],
        db_path=os.environ.get("WEDGE_DB_PATH", "./wedge.db"),
        bright_data_call_cap=int(os.environ.get("WEDGE_BRIGHT_DATA_CALL_CAP", "40")),
    )
