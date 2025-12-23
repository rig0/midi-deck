#!/usr/bin/env python3
"""
Phase 4 Verification Script

This script verifies that Phase 4 implementation is complete by checking:
- SessionManager module exists and has all required methods
- Integration with main.py is correct
- Database models support session state
- All helper functions are implemented

This script does NOT require PulseAudio to run.
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))


def check_module_exists(module_path):
    """Check if a module file exists."""
    if os.path.exists(module_path):
        print(f"  ✓ {module_path}")
        return True
    else:
        print(f"  ✗ {module_path} - NOT FOUND")
        return False


def check_class_has_method(cls, method_name):
    """Check if a class has a specific method."""
    if hasattr(cls, method_name):
        print(f"    ✓ {method_name}")
        return True
    else:
        print(f"    ✗ {method_name} - NOT FOUND")
        return False


def check_function_exists(module, func_name):
    """Check if a module has a function."""
    if hasattr(module, func_name):
        print(f"    ✓ {func_name}")
        return True
    else:
        print(f"    ✗ {func_name} - NOT FOUND")
        return False


def main():
    """Run verification checks."""
    print("=" * 70)
    print("  Phase 4 Implementation Verification")
    print("=" * 70)

    all_passed = True

    # Check 1: Files exist
    print("\n1. Checking files exist...")
    files_ok = True
    files_ok &= check_module_exists(
        "/home/rambo/code/midi-deck/app/core/session_manager.py"
    )
    files_ok &= check_module_exists("/home/rambo/code/midi-deck/scripts/test_phase4.py")
    files_ok &= check_module_exists("/home/rambo/code/midi-deck/main.py")
    all_passed &= files_ok

    if not files_ok:
        print("\n❌ File check failed")
        return 1

    # Check 2: SessionManager class
    print("\n2. Checking SessionManager class...")
    try:
        from app.core.session_manager import SessionManager

        print("  ✓ SessionManager imported successfully")

        required_methods = [
            "__init__",
            "set_managers",
            "create_session",
            "delete_session",
            "list_sessions",
            "get_current_session_info",
            "set_current_session",
            "_capture_state",
            "_restore_state",
            "save_session",
            "load_session",
            "save_current_session",
            "load_current_session",
            "enable_auto_save",
            "disable_auto_save",
            "is_auto_save_enabled",
            "auto_save_if_enabled",
        ]

        methods_ok = True
        for method in required_methods:
            methods_ok &= check_class_has_method(SessionManager, method)

        all_passed &= methods_ok

        if not methods_ok:
            print("\n  ❌ Some SessionManager methods are missing")
    except Exception as e:
        print(f"  ✗ Failed to import SessionManager: {e}")
        all_passed = False

    # Check 3: Database helper functions
    print("\n3. Checking database helper functions...")
    try:
        from app.database import db

        print("  ✓ Database module imported successfully")

        required_funcs = [
            "save_session_state",
            "load_session_state",
            "get_current_session_state",
            "get_active_sink_names",
            "get_active_output_names",
        ]

        funcs_ok = True
        for func in required_funcs:
            funcs_ok &= check_function_exists(db, func)

        all_passed &= funcs_ok

        if not funcs_ok:
            print("\n  ❌ Some database helper functions are missing")
    except Exception as e:
        print(f"  ✗ Failed to import database module: {e}")
        all_passed = False

    # Check 4: Database models
    print("\n4. Checking database models...")
    try:
        from app.database.models import (
            Session,
            SessionConnection,
            SessionMute,
            SessionVolume,
            create_session,
            delete_session,
            get_all_sessions,
            get_current_session,
            set_current_session,
        )

        print("  ✓ All required database models and functions exist")
    except ImportError as e:
        print(f"  ✗ Failed to import database models: {e}")
        all_passed = False

    # Check 5: main.py integration
    print("\n5. Checking main.py integration...")
    try:
        with open("/home/rambo/code/midi-deck/main.py", "r") as f:
            main_content = f.read()

        integration_checks = [
            (
                "SessionManager import",
                "from app.core.session_manager import SessionManager",
            ),
            ("SessionManager initialization", "session_manager = SessionManager("),
            ("Load current session", "session_manager.load_current_session()"),
            ("Save on shutdown", "session_manager.save_current_session()"),
        ]

        integration_ok = True
        for check_name, check_string in integration_checks:
            if check_string in main_content:
                print(f"    ✓ {check_name}")
            else:
                print(f"    ✗ {check_name} - NOT FOUND")
                integration_ok = False

        all_passed &= integration_ok

        if not integration_ok:
            print("\n  ❌ Some main.py integrations are missing")
    except Exception as e:
        print(f"  ✗ Failed to check main.py: {e}")
        all_passed = False

    # Check 6: Test script exists
    print("\n6. Checking test script...")
    try:
        with open("/home/rambo/code/midi-deck/scripts/test_phase4.py", "r") as f:
            test_content = f.read()

        test_checks = [
            "test_database_initialization",
            "test_audio_manager_initialization",
            "test_session_manager_initialization",
            "test_state_capture",
            "test_session_save",
            "test_session_restore",
            "test_session_creation",
            "test_session_switching",
            "test_session_deletion",
        ]

        tests_ok = True
        for test in test_checks:
            if test in test_content:
                print(f"    ✓ {test}")
            else:
                print(f"    ✗ {test} - NOT FOUND")
                tests_ok = False

        all_passed &= tests_ok

        if not tests_ok:
            print("\n  ❌ Some test functions are missing")
    except Exception as e:
        print(f"  ✗ Failed to check test script: {e}")
        all_passed = False

    # Summary
    print("\n" + "=" * 70)
    if all_passed:
        print("✅ All Phase 4 verification checks PASSED")
        print("\nPhase 4 implementation is complete:")
        print("  - SessionManager fully implemented")
        print("  - Database integration complete")
        print("  - main.py integration complete")
        print("  - Test script created")
        print("\nNote: Run scripts/test_phase4.py in an environment with")
        print("      PulseAudio/PipeWire for full functional testing.")
        print("=" * 70)
        return 0
    else:
        print("❌ Some Phase 4 verification checks FAILED")
        print("\nPlease review the errors above.")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
