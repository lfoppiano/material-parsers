import argparse

from material_parsers.service import init

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Materials parsing and identification python tools service.")

    parser.add_argument("--host", required=False, default='0.0.0.0', help="Hostname.")
    parser.add_argument("--port", required=False, default=8080, help="Listening port.")
    parser.add_argument("--config", required=False, help="Path to the configuration file.")

    args = parser.parse_args()

    host = args.host
    port = args.port
    config = args.config

    init(host, port, config)
