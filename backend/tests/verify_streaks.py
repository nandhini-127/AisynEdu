import asyncio
import uuid
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.entities import User
from app.services.auth_service import AuthService
from app.analytics.service import AnalyticsService


async def run_scenario_tests():
    print("=== RUNNING COMPREHENSIVE STREAK VERIFICATION ===")

    # 1. New user registration & default streak
    async with AsyncSessionLocal() as session:
        test_email = f"streak_tester_{uuid.uuid4().hex[:6]}@edunex.test"
        user = User(
            id=uuid.uuid4(),
            email=test_email,
            name="Streak Tester",
            hashed_password="pw",
            current_streak=0,
            longest_streak=0,
            last_login_date=None,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        print(f"Test 1 (New User Default): current_streak={user.current_streak}, longest={user.longest_streak}, last_date={user.last_login_date}")
        assert user.current_streak == 0
        assert user.longest_streak == 0
        assert user.last_login_date is None

        # 2. First login on Nov 14
        d1 = date(2026, 11, 14)
        inc1 = AuthService.update_login_streak(user, target_date=d1)
        await session.commit()
        print(f"Test 2 (First Login Nov 14): inc={inc1}, streak={user.current_streak}, longest={user.longest_streak}, date={user.last_login_date}")
        assert inc1 is True
        assert user.current_streak == 1
        assert user.longest_streak == 1
        assert user.last_login_date == d1

        # 3. Same day second login on Nov 14
        inc2 = AuthService.update_login_streak(user, target_date=d1)
        await session.commit()
        print(f"Test 3 (Second Login Same Day Nov 14): inc={inc2}, streak={user.current_streak}, longest={user.longest_streak}")
        assert inc2 is False
        assert user.current_streak == 1
        assert user.longest_streak == 1

        # 4. Consecutive day login on Nov 15
        d2 = date(2026, 11, 15)
        inc3 = AuthService.update_login_streak(user, target_date=d2)
        await session.commit()
        print(f"Test 4 (Consecutive Day Nov 15): inc={inc3}, streak={user.current_streak}, longest={user.longest_streak}")
        assert inc3 is True
        assert user.current_streak == 2
        assert user.longest_streak == 2

        # 5. Consecutive days Nov 16, 17, 18 -> streak 5
        for d, expected_streak in [(date(2026, 11, 16), 3), (date(2026, 11, 17), 4), (date(2026, 11, 18), 5)]:
            inc = AuthService.update_login_streak(user, target_date=d)
            assert user.current_streak == expected_streak
            assert user.longest_streak == expected_streak
        await session.commit()
        print(f"Test 5 (Consecutive to Nov 18): streak={user.current_streak}, longest={user.longest_streak}")
        assert user.current_streak == 5
        assert user.longest_streak == 5

        # 6. Missed Nov 19, Login on Nov 20 -> streak resets to 1, longest remains 5
        d_missed = date(2026, 11, 20)
        inc_reset = AuthService.update_login_streak(user, target_date=d_missed)
        await session.commit()
        print(f"Test 6 (After Missed Day Nov 20): inc={inc_reset}, streak={user.current_streak}, longest={user.longest_streak}")
        assert inc_reset is True
        assert user.current_streak == 1
        assert user.longest_streak == 5  # Preserved!

        # 7. Check AnalyticsService.get_student_analytics
        analytics = await AnalyticsService.get_student_analytics(session, user.id)
        print(f"Test 7 (Analytics API Output): study_streak_days={analytics['study_streak_days']}, current_streak={analytics['current_streak']}, longest={analytics['longest_streak']}")
        assert analytics["study_streak_days"] == 1
        assert analytics["current_streak"] == 1
        assert analytics["longest_streak"] == 5

        # 8. Timezone boundary test (Asia/Kolkata)
        utc_moment = datetime(2026, 11, 14, 18, 45, 0, tzinfo=timezone.utc)
        ist_tz = ZoneInfo("Asia/Kolkata")
        ist_date = utc_moment.astimezone(ist_tz).date()
        print(f"Test 8 (Timezone Boundary): UTC 18:45 -> IST Date {ist_date}")
        assert ist_date == date(2026, 11, 15)

        # Clean up test user
        await session.delete(user)
        await session.commit()
        print("=== ALL STREAK SCENARIOS VERIFIED SUCCESSFULLY ===")


if __name__ == "__main__":
    asyncio.run(run_scenario_tests())

