#!/usr/bin/env python3
import argparse
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

# ----------------------------
# Logging Configuration
# ----------------------------

# Create data and logs directories if they don't exist
Path("./data").mkdir(exist_ok=True)
Path("./logs").mkdir(exist_ok=True)

# Create logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Create formatter
formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(module)s: %(message)s",
    datefmt="%m/%d/%Y %H:%M:%S",
)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Rotating file handler
file_handler = RotatingFileHandler(
    "logs/midi_deck.log",
    maxBytes=5 * 1024 * 1024,  # 5MB per file
    backupCount=3,  # Keep 3 backups (main.log.1, main.log.2, main.log.3)
)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


def main():
    """Main entry point for MIDI Deck application."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="MIDI Deck Audio Controller")
    parser.add_argument(
        "--web-only",
        action="store_true",
        help="Run web interface only (for configuration)",
    )
    parser.add_argument("--no-web", action="store_true", help="Disable web interface")
    parser.add_argument(
        "--config", type=str, help="Path to database file (default: data/midi_deck.db)"
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    # Update log level if debug flag is set
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")

    logger.info("Starting MIDI Deck Application...")
    logger.info(
        f"Arguments: web_only={args.web_only}, no_web={args.no_web}, config={args.config}"
    )

    # TODO: Phase 2 - Initialize database
    # db_path = args.config or 'data/midi_deck.db'
    # init_database(db_path)

    # TODO: Phase 4 - Load or create default session
    # session_manager = SessionManager()
    # session_manager.load_current_session()

    if args.web_only:
        # TODO: Phase 5-6 - Run web interface only
        logger.info("Web-only mode: Starting web interface...")
        # app = create_app()
        # run_web_server(app)
        logger.warning("Web interface not yet implemented (Phase 5-6)")
        sys.exit(0)
    else:
        # TODO: Phase 1 (later steps) - Start MIDI controller
        logger.info("MIDI mode: Starting MIDI controller...")
        # controller = MidiController()

        # TODO: Phase 7 - Start web interface in background if enabled
        if not args.no_web:
            # from threading import Thread
            # app = create_app()
            # web_thread = Thread(target=run_web_server, args=(app,), daemon=True)
            # web_thread.start()
            logger.info(
                "Web interface will be started in background (not yet implemented)"
            )

        # TODO: Phase 1 (later steps) - Run main MIDI event loop (blocking)
        try:
            logger.info("MIDI event loop starting (not yet implemented)...")
            logger.warning("MIDI controller not yet implemented (Phase 1 continuation)")
            # controller.run()
        except KeyboardInterrupt:
            logger.info("Shutting down gracefully...")
            # TODO: Phase 4 - Save session on shutdown
            # session_manager.save_current_session()
            sys.exit(0)


if __name__ == "__main__":
    main()
