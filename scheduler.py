import asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy import and_
from functools import partial
from extensions import db, scheduler
from models import NotificationSetting, ReminderLog, Expense, FCMToken, User
from utils import send_email
from firebase import firebase_messaging as messaging
from flask import Flask


async def send_single_push(token, title, body, app: Flask, click_action_url=None):
    """
    Send a push notification to a single device token.

    click_action_url: URL to open when notification is clicked (Android/iOS/web).
    Defaults to app.config["FRONTEND_URL"] if not provided.
    """
    if click_action_url is None:
        click_action_url =  f"{app.config.get('FRONTEND_URL')}/login"

    notification = messaging.Notification(title=title, body=body)

    android_config = messaging.AndroidConfig(
        notification=messaging.AndroidNotification(
            click_action="FLUTTER_NOTIFICATION_CLICK" if click_action_url else None
        )
    )

    apns_config = messaging.APNSConfig(
        payload=messaging.APNSPayload(
            aps=messaging.Aps(
                category="FLUTTER_NOTIFICATION_CLICK" if click_action_url else None
            )
        )
    )

    webpush_config = None
    if click_action_url:
        webpush_config = messaging.WebpushConfig(
            fcm_options=messaging.WebpushFCMOptions(link=click_action_url)
        )

    message = messaging.Message(
        notification=notification,
        android=android_config,
        apns=apns_config,
        webpush=webpush_config,
        token=token
    )

    try:
        messaging.send(message)
        return True, token
    except Exception as e:
        print(f"Error sending push to token {token}: {e}")
        return False, token


def send_push_notification(user_id: int, app: Flask, title="Expense Reminder", body="Time to add your expenses", click_action_url=None):
    """
    Send push notifications to all devices of a user.
    Uses app.config["FRONTEND_URL"] if click_action_url is not provided.
    """
    with app.app_context():
        tokens = [t.token for t in FCMToken.query.filter_by(user_id=user_id).all()]
        if not tokens:
            print(f"No device tokens found for user {user_id}")
            return

        async def send_all():
            tasks = [send_single_push(token, title, body, app, click_action_url) for token in tokens]
            return await asyncio.gather(*tasks)

        results = asyncio.run(send_all())

        success_count = sum(1 for success, _ in results if success)
        failure_tokens = [token for success, token in results if not success]

        if failure_tokens:
            FCMToken.query.filter(FCMToken.token.in_(failure_tokens)).delete(synchronize_session=False)
            db.session.commit()

        print(f"Push notification sent to user {user_id}: {success_count} success, {len(failure_tokens)} failed")


def send_email_reminder(user_id: int, app: Flask):
    with app.app_context():
        user = User.query.get(user_id)
        if not user or not user.email:
            print(f"No email found for user {user_id}")
            return
        try:
            send_email(user_email=user.email, file_path=None)
            print(f"Email reminder sent to {user.email}")
        except Exception as e:
            print(f"Failed to send email to {user.email}: {e}")


def send_daily_push(user_id: int, app):
    with app.app_context():
        now = datetime.now(timezone.utc)
        send_push_notification(user_id, app)

        reminder = ReminderLog(user_id=user_id, push_sent_at=now)
        db.session.add(reminder)
        db.session.commit()

        scheduler.add_job(
            partial(check_and_send_email, reminder_id=reminder.id, app=app),
            trigger="date",
            run_date=now + timedelta(hours=1),
            id=f"email_check_{reminder.id}",
            replace_existing=True
        )


def check_and_send_email(reminder_id: int, app):
    with app.app_context():
        reminder = ReminderLog.query.get(reminder_id)
        if not reminder or reminder.email_sent:
            return

        start = reminder.push_sent_at
        end = start + timedelta(hours=1)

        expense_exists = db.session.query(Expense.id).filter(
            and_(
                Expense.user_id == reminder.user_id,
                Expense.date >= start,
                Expense.date <= end
            )
        ).first()

        if not expense_exists:
            send_email_reminder(reminder.user_id, app)
            reminder.email_sent = True
            db.session.commit()


def schedule_user_daily_push(setting: NotificationSetting, app):
    job_id = f"daily_push_{setting.user_id}"

    scheduler.add_job(
        partial(send_daily_push, user_id=setting.user_id, app=app),
        trigger="cron",
        hour=setting.reminder_time.hour,
        minute=setting.reminder_time.minute,
        timezone=setting.timezone,
        id=job_id,
        replace_existing=True
    )


def load_all_user_jobs(app):
    with app.app_context():
        settings = NotificationSetting.query.filter_by(enabled=True).all()
        for setting in settings:
            schedule_user_daily_push(setting, app)
