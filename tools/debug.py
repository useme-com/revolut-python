import argparse
import json
import logging
import os
from revolut.session import TemporarySession, RenewableSession, TokenProvider


class Config(object):
    stored_keys = ("client_id", "jwt", "refresh_token", "access_token", "auth_code")
    default_config_file = os.path.join(os.path.expanduser("~"), ".revolut-python.json")
    config_info = (
        "Config requires "
        "one of the following key combinations: "
        "(client_id, jwt, refresh_token), "
        "(client_id, jwt, auth_code), "
        "(access_token,)"
    )

    def __init__(self, config_file=None):
        self.data = {}
        self.config_file = config_file or self.default_config_file

    def load_file_config(self):
        try:
            with open(self.config_file, "r") as fh:
                self.data.update(json.load(fh))
        except FileNotFoundError:
            if self.config_file != self.default_config_file:
                raise

    def store_file_config(self):
        with open(self.config_file, "w+") as fh:
            stored_data = {}
            for k in self.stored_keys:
                if v := self.data.get(k):
                    stored_data[k] = v
            json.dump(stored_data, fh, indent=2)

    def get_cli_data(self):
        self.parser = argparse.ArgumentParser(
            description="Dump data from Revolut account", epilog=self.config_info
        )
        self.parser.add_argument(
            "-c",
            dest="config_file",
            nargs="?",
            default=self.config_file,
            help="Path to JSON config file; it can serve as defaults storage "
            "as command line arguments have precedence over those within the file",
        )
        self.parser.add_argument(
            "-v",
            dest="verbosity",
            action="count",
            default=0,
            help="Verbosity (repeat to increase; -v for INFO, -vv for DEBUG",
        )
        self.parser.add_argument("-u", dest="client_id", nargs="?", help="Client ID")
        self.parser.add_argument("-t", dest="auth_code", nargs="?", help="Auth code")
        self.parser.add_argument("-j", dest="jwt", nargs="?", help="JWT")
        self.parser.add_argument(
            "-r", dest="refresh_token", nargs="?", help="Refresh token"
        )
        self.parser.add_argument(
            "-a", dest="access_token", nargs="?", help="Access token"
        )
        self.parser.add_argument(
            "-w",
            dest="write_config",
            action="store_true",
            default=False,
            help="Write config back to file",
        )
        self._cli_config = self.parser.parse_args()
        level = logging.WARNING
        if self._cli_config.verbosity == 1:
            level = logging.INFO
        elif self._cli_config.verbosity > 1:
            level = logging.DEBUG
        logging.basicConfig(level=level, format="%(asctime)-15s %(message)s")
        return self._cli_config

    def load_config(self):
        cli_data = self.get_cli_data()
        self.config_file = cli_data.config_file
        self.load_file_config()
        for k in self.stored_keys:
            clival = getattr(cli_data, k)
            if clival:
                self.data[k] = clival

    def write_config_if_needed(self):
        if self._cli_config.write_config:
            self.store_file_config()

    def get_session(self):
        """Check what session class is available with current settings. Initialize it and
        return. Long-term sessions are preferred."""
        if set(("client_id", "jwt", "refresh_token")).issubset(self.data.keys()):
            return RenewableSession(
                self.data["refresh_token"],
                self.data["client_id"],
                self.data["jwt"],
                access_token=self.data.get("access_token", None),
            )
        elif set(("client_id", "jwt", "auth_code")).issubset(self.data.keys()):
            tp = TokenProvider(
                self.data["auth_code"], self.data["client_id"], self.data["jwt"]
            )
            self.data["refresh_token"] = tp.refresh_token
            return RenewableSession(
                self.data["refresh_token"], self.data["client_id"], self.data["jwt"]
            )
        elif "access_token" in self.data.keys():
            return TemporarySession(self.data["access_token"])
        else:
            raise ValueError(
                "Not enough data to construct Revolut session.\n"
                "{:s}\n"
                "Current keys are: ({:s})".format(
                    self.config_info, ", ".join(self.data.keys())
                )
            )


if __name__ == "__main__":
    import ipdb
    import sys
    from revolut import Client

    conf = Config()
    conf.load_config()
    try:
        session = conf.get_session()
    except ValueError as e:
        print(str(e), file=sys.stderr)
        conf.parser.print_usage(file=sys.stderr)
        sys.exit(1)
    conf.write_config_if_needed()
    cli = Client(session)
    print("-" * 50)
    print(
        "Now you should have an authorized revolut.Client instance under the `cli` variable."
    )
    print("-" * 50)

    ipdb.set_trace()
