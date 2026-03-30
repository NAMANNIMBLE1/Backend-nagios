from dotenv import load_dotenv
import os
load_dotenv()

def get_config():
    # required .env values
    required_vars = ["DB_HOST", "DB_USER", "DB_PASSWORD","DB_NAME","FORECAST_DAYS"]
    config = {}

    for credential in required_vars:
        val = os.getenv(credential)
        if val is None:
            raise ValueError(f"missing environmental variables: {val}")
        config[credential] = val

    return config


if __name__ == "__main__":
    print(get_config())