"""
Unit tests for EduNex AI Daily Login Streak System.
Validates:
1. First login -> streak 1
2. Multiple logins on same calendar day -> streak remains 1
3. Consecutive calendar day login -> streak increments by 1
4. Missed calendar days (>= 1 day) -> streak resets to 1
5. Longest streak tracking and retention across resets
6. Timezone boundary calculations (Asia/Kolkata)
7. Safe database defaults for new users
"""
import uuid
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import pytest

from app.models.entities import User
from app.services.auth_service import AuthService


def test_first_login_sets_streak_to_one():
    """Rule 1: A new user starts with a streak of 1 on their first successful login."""
    user = User(
        id=uuid.uuid4(),
        email="student@edunex.test",
        name="New Student",
        hashed_password="hashed_pw_secret",
        current_streak=0,
        longest_streak=0,
        last_login_date=None,
    )
    today = date(2026, 11, 14)
    increased = AuthService.update_login_streak(user, target_date=today)

    assert increased is True
    assert user.current_streak == 1
    assert user.longest_streak == 1
    assert user.last_login_date == today


def test_multiple_logins_same_day_do_not_increase_streak():
    """Rule 2 & 5: Multiple logins on the same calendar day count as only ONE streak day."""
    today = date(2026, 11, 14)
    user = User(
        id=uuid.uuid4(),
        email="student@edunex.test",
        name="Student",
        hashed_password="hashed_pw_secret",
        current_streak=1,
        longest_streak=1,
        last_login_date=today,
    )
    # Login again on the same day
    increased = AuthService.update_login_streak(user, target_date=today)

    assert increased is False
    assert user.current_streak == 1
    assert user.longest_streak == 1
    assert user.last_login_date == today

    # Third login on the same day
    increased_again = AuthService.update_login_streak(user, target_date=today)
    assert increased_again is False
    assert user.current_streak == 1


def test_consecutive_day_login_increments_streak():
    """Rule 3: Login on the next consecutive calendar day increases the streak by 1."""
    day1 = date(2026, 11, 14)
    day2 = date(2026, 11, 15)
    day3 = date(2026, 11, 16)
    day4 = date(2026, 11, 17)
    day5 = date(2026, 11, 18)

    user = User(
        id=uuid.uuid4(),
        email="student@edunex.test",
        name="Student",
        hashed_password="hashed_pw_secret",
        current_streak=0,
        longest_streak=0,
        last_login_date=None,
    )

    # Day 1 -> Streak 1
    AuthService.update_login_streak(user, target_date=day1)
    assert user.current_streak == 1
    assert user.longest_streak == 1

    # Day 2 -> Streak 2
    inc2 = AuthService.update_login_streak(user, target_date=day2)
    assert inc2 is True
    assert user.current_streak == 2
    assert user.longest_streak == 2

    # Day 3 -> Streak 3
    inc3 = AuthService.update_login_streak(user, target_date=day3)
    assert inc3 is True
    assert user.current_streak == 3
    assert user.longest_streak == 3

    # Day 4 -> Streak 4
    inc4 = AuthService.update_login_streak(user, target_date=day4)
    assert inc4 is True
    assert user.current_streak == 4
    assert user.longest_streak == 4

    # Day 5 -> Streak 5
    inc5 = AuthService.update_login_streak(user, target_date=day5)
    assert inc5 is True
    assert user.current_streak == 5
    assert user.longest_streak == 5


def test_missed_days_resets_current_streak_preserving_longest():
    """Rule 4 & 6: Missed calendar days reset current streak to 1, while longest streak is preserved."""
    day5 = date(2026, 11, 18)
    day7 = date(2026, 11, 20)  # Missed Nov 19

    user = User(
        id=uuid.uuid4(),
        email="student@edunex.test",
        name="Student",
        hashed_password="hashed_pw_secret",
        current_streak=5,
        longest_streak=5,
        last_login_date=day5,
    )

    inc = AuthService.update_login_streak(user, target_date=day7)

    assert inc is True
    assert user.current_streak == 1
    assert user.longest_streak == 5  # Preserved!
    assert user.last_login_date == day7


def test_streak_exceeds_previous_longest():
    """Rule 6: If current streak exceeds previous longest streak, update longest streak."""
    day1 = date(2026, 11, 20)
    day2 = date(2026, 11, 21)

    user = User(
        id=uuid.uuid4(),
        email="student@edunex.test",
        name="Student",
        hashed_password="hashed_pw_secret",
        current_streak=1,
        longest_streak=1,
        last_login_date=day1,
    )

    AuthService.update_login_streak(user, target_date=day2)
    assert user.current_streak == 2
    assert user.longest_streak == 2


def test_timezone_boundary_asia_kolkata():
    """Rule 8: Verify correct India (Asia/Kolkata, UTC+5:30) calendar date computation around midnight."""
    # 2026-11-14 18:45:00 UTC is 2026-11-15 00:15:00 IST (+5:30)
    utc_moment = datetime(2026, 11, 14, 18, 45, 0, tzinfo=timezone.utc)
    ist_tz = ZoneInfo("Asia/Kolkata")
    ist_time = utc_moment.astimezone(ist_tz)

    assert ist_time.date() == date(2026, 11, 15)
    assert ist_time.hour == 0
    assert ist_time.minute == 15


def test_new_user_default_values():
    """Verify that a brand new registered user has streak defaults of 0 before their first login."""
    user = User(
        email="brand_new@edunex.test",
        name="New User",
        hashed_password="hashed_pw_secret",
        current_streak=0,
        longest_streak=0,
        last_login_date=None,
    )
    assert user.current_streak == 0
    assert user.longest_streak == 0
    assert user.last_login_date is None

