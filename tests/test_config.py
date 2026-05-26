from wedge.config import load_config


def test_load_config_reads_env():
    cfg = load_config()
    assert cfg.anthropic_api_key == "test-anthropic"
    assert cfg.bright_data_token == "test-bd"
    assert cfg.bright_data_call_cap == 40
    assert cfg.db_path == ":memory:"
