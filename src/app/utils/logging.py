# utils/logging.py
import logging

def setup_logging(debug_mode: bool = False) -> None:
    logging.basicConfig(
        level=logging.DEBUG if debug_mode else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
