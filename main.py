#!/usr/bin/env python3
import argparse
import logging
import signal
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.core.audio_manager import AudioManager
from app.core.loopback_manager import LoopbackManager
from app.core.midi_controller import MidiController
from app.core.session_manager import SessionManager
from app.database import init_database

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

    # Phase 2 - Initialize database
    db_path = args.config or "data/midi_deck.db"
    logger.info(f"Initializing database at: {db_path}")
    try:
        init_database(db_path)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}", exc_info=True)
        sys.exit(1)

    # Phase 3 - Initialize AudioManager and LoopbackManager
    logger.info("Initializing audio subsystems...")
    try:
        audio_manager = AudioManager()
        loopback_manager = LoopbackManager(audio_manager.pulse)
        logger.info("Audio subsystems initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize audio subsystems: {e}", exc_info=True)
        sys.exit(1)

    # Phase 3 - Create virtual sinks from database
    logger.info("Creating virtual sinks from database configuration...")
    try:
        if audio_manager.initialize_sinks_from_database():
            logger.info("Virtual sinks initialized successfully")
        else:
            logger.warning("Some virtual sinks failed to initialize")
    except Exception as e:
        logger.error(f"Failed to initialize virtual sinks: {e}", exc_info=True)
        # Don't exit - continue with degraded functionality

    # Phase 4 - Initialize SessionManager and load current session
    logger.info("Initializing session manager...")
    try:
        session_manager = SessionManager(audio_manager, loopback_manager)

        # Load or create default session (this will restore volumes, mutes, and connections)
        if session_manager.load_current_session():
            logger.info("Current session loaded successfully")
        else:
            logger.warning("Failed to load current session, continuing with defaults")
    except Exception as e:
        logger.error(f"Failed to initialize session manager: {e}", exc_info=True)
        # Create a placeholder session manager for shutdown
        session_manager = SessionManager()
        logger.warning("Continuing without session management")

    if args.web_only:
        # TODO: Phase 5-6 - Run web interface only
        logger.info("Web-only mode: Starting web interface...")
        # app = create_app()
        # run_web_server(app)
        logger.warning("Web interface not yet implemented (Phase 5-6)")
        sys.exit(0)
    else:
        # Phase 1 - Initialize MIDI controller
        logger.info("MIDI mode: Initializing MIDI controller...")
        try:
            controller = MidiController(audio_manager, loopback_manager)
            logger.info("MIDI controller initialized")
        except Exception as e:
            logger.error(f"Failed to initialize MIDI controller: {e}", exc_info=True)
            sys.exit(1)

        # TODO: Phase 7 - Start web interface in background if enabled
        if not args.no_web:
            # from threading import Thread
            # app = create_app()
            # web_thread = Thread(target=run_web_server, args=(app,), daemon=True)
            # web_thread.start()
            logger.info(
                "Web interface will be started in background (not yet implemented)"
            )

        # Setup signal handlers for graceful shutdown
        shutdown_event = {"triggered": False}

        def signal_handler(signum, frame):
            if not shutdown_event["triggered"]:
                shutdown_event["triggered"] = True
                logger.info("Shutdown signal received, cleaning up...")
                controller.stop()
                # Phase 4 - Save session on shutdown
                try:
                    logger.info("Saving current session state before shutdown...")
                    if session_manager.save_current_session():
                        logger.info("Session state saved successfully")
                    else:
                        logger.warning("Failed to save session state")
                except Exception as e:
                    logger.error(f"Error saving session on shutdown: {e}")
                sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Phase 1 - Run main MIDI event loop (blocking)
        try:
            logger.info("Starting MIDI event loop...")
            controller.run()
        except KeyboardInterrupt:
            logger.info("Shutting down gracefully...")
            controller.stop()
            # Phase 4 - Save session on shutdown
            try:
                logger.info("Saving current session state before shutdown...")
                if session_manager.save_current_session():
                    logger.info("Session state saved successfully")
                else:
                    logger.warning("Failed to save session state")
            except Exception as e:
                logger.error(f"Error saving session on shutdown: {e}")
            sys.exit(0)
        except Exception as e:
            logger.error(f"Fatal error in MIDI event loop: {e}", exc_info=True)
            controller.stop()
            sys.exit(1)


if __name__ == "__main__":
    main()
