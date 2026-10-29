import os
import sqlite3
import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import logging
from typing import Optional

try:
    from livekit.agents import function_tool
except ImportError:
    def function_tool(func):
        return func

logger = logging.getLogger("MJ_Scheduler")
logger.setLevel(logging.INFO)

DB_PATH = "nion_reminders.db"

def init_db():
    """Initialize the SQLite database for reminders and tasks."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            task TEXT NOT NULL,
            due_time TEXT NOT NULL,
            notify_time TEXT NOT NULL,
            email_recipient TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

init_db()

def send_email_notification(subject: str, body: str, recipient_email: Optional[str] = None):
    """
    Sends an email notification using SMTP credentials from .env.
    Falls back to logging if SMTP is not configured.
    """
    sender_email = os.getenv("SENDER_EMAIL") or os.getenv("GMAIL_USER")
    sender_password = os.getenv("SENDER_APP_PASSWORD") or os.getenv("GMAIL_APP_PASSWORD")
    target_email = recipient_email or os.getenv("RECEIVER_EMAIL") or sender_email

    if not sender_email or not sender_password:
        logger.warning("SMTP credentials not fully set in .env (SENDER_EMAIL / SENDER_APP_PASSWORD). Notification logged:")
        logger.info(f"[EMAIL] [EMAIL ALERT] To: {target_email} | Subject: {subject} | Body: {body}")
        return False

    try:
        msg = MIMEMultipart()
        msg['From'] = f"Zora AI Assistant <{sender_email}>"
        msg['To'] = target_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        logger.info(f"[OK] Email notification sent to {target_email}")
        return True
    except Exception as e:
        logger.error(f"[FAIL] Failed to send email notification: {e}")
        return False

def parse_time(due_time_str: str) -> tuple[datetime, datetime]:
    """
    Parses a due time string (e.g., '2026-08-15 15:00', '15:00', 'tomorrow 15:00', 'in 30 mins').
    Returns (due_datetime, notify_datetime) where notify_datetime is 10 mins prior.
    """
    now = datetime.now()
    due_dt = None

    due_time_str_clean = due_time_str.strip().lower()

    if "in " in due_time_str_clean:
        # e.g., "in 30 mins", "in 1 hour"
        parts = due_time_str_clean.replace("in ", "").split()
        if len(parts) >= 2 and parts[0].isdigit():
            val = int(parts[0])
            unit = parts[1]
            if "min" in unit:
                due_dt = now + timedelta(minutes=val)
            elif "hour" in unit:
                due_dt = now + timedelta(hours=val)
            elif "day" in unit:
                due_dt = now + timedelta(days=val)

    if not due_dt:
        # Try standard ISO formats
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%H:%M", "%I:%M %p"):
            try:
                parsed = datetime.strptime(due_time_str_clean, fmt)
                if fmt in ("%H:%M", "%I:%M %p"):
                    due_dt = now.replace(hour=parsed.hour, minute=parsed.minute, second=0, microsecond=0)
                    if due_dt < now:
                        due_dt += timedelta(days=1)
                else:
                    due_dt = parsed
                break
            except ValueError:
                continue

    if not due_dt:
        # Fallback to 1 hour from now if unparseable
        due_dt = now + timedelta(hours=1)

    notify_dt = due_dt - timedelta(minutes=10)
    if notify_dt < now:
        notify_dt = now  # Trigger immediately if less than 10 mins away

    return due_dt, notify_dt

@function_tool()
async def set_reminder_tool(task: str, due_time: str, email: str = "") -> str:
    """
    Sets a reminder/todo for the user with an automatic email notification 10 minutes before the event.
    Use this when the user says something like:
    - 'MJ kalke amar exam/pora ache 3tai, mone karae dio'
    - 'Remind me to study tomorrow at 3 PM'
    - 'Set a reminder for my meeting in 30 minutes'

    Parameters:
    - task: Description of the task or exam (e.g. 'Pora / Exam session')
    - due_time: Time of the event (e.g. '2026-08-15 15:00', '15:00', 'tomorrow 15:00', 'in 30 mins')
    - email: Optional recipient email address.
    """
    try:
        due_dt, notify_dt = parse_time(due_time)
        now_str = datetime.now().isoformat()

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO reminders (user_id, task, due_time, notify_time, email_recipient, status, created_at)
            VALUES (?, ?, ?, ?, ?, 'pending', ?)
        """, ("Neon", task, due_dt.isoformat(), notify_dt.isoformat(), email, now_str))
        conn.commit()
        reminder_id = cursor.lastrowid
        conn.close()

        due_formatted = due_dt.strftime("%d %B %Y at %I:%M %p")
        notify_formatted = notify_dt.strftime("%I:%M %p")

        return (f"[OK] Boss, reminder set successfully! (ID: {reminder_id})\n"
                f"[NOTE] Task: {task}\n"
                f"[ALARM] Event Time: {due_formatted}\n"
                f"[EMAIL] Email Alert: Scheduled for {notify_formatted} (10 mins before).")
    except Exception as e:
        return f"Error setting reminder: {e}"

@function_tool()
async def get_reminders_tool() -> str:
    """
    Lists all pending reminders and tasks stored for the user.
    Use when user asks 'what are my reminders?', 'amar ki ki task ache', or 'check my todo list'.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, task, due_time, notify_time, status FROM reminders WHERE status='pending' ORDER BY due_time ASC")
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return "Boss, apner kono pending reminder ba task nei."

        lines = ["[NOTE] **Your Pending Reminders & Tasks:**"]
        for row in rows:
            r_id, task, due_str, notify_str, status = row
            try:
                due_dt = datetime.fromisoformat(due_str)
                due_formatted = due_dt.strftime("%d %b, %I:%M %p")
            except Exception:
                due_formatted = due_str
            lines.append(f"- [ID {r_id}] **{task}** - Scheduled for: {due_formatted}")

        return "\n".join(lines)
    except Exception as e:
        return f"Error fetching reminders: {e}"

async def background_reminder_loop():
    """
    Continuous background loop that checks for reminders reaching their notify_time
    and dispatches email alerts.
    """
    logger.info("[ALARM] Background Reminder & Email Loop initialized.")
    while True:
        try:
            now = datetime.now()
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT id, task, due_time, notify_time, email_recipient FROM reminders WHERE status='pending'")
            rows = cursor.fetchall()

            for row in rows:
                r_id, task, due_str, notify_str, email_recipient = row
                try:
                    notify_dt = datetime.fromisoformat(notify_str)
                    due_dt = datetime.fromisoformat(due_str)
                except Exception:
                    continue

                if now >= notify_dt:
                    mins_left = max(1, int((due_dt - now).total_seconds() / 60))
                    subject = f"[ALARM] [Zora Alert] Reminder: {task}"
                    body = (f"Boss,\n\n"
                            f"Apner task '{task}' start hothe r {mins_left} minute baki ache!\n"
                            f"Scheduled Time: {due_dt.strftime('%I:%M %p')}\n\n"
                            f"Porte jan ba task-e join korun!\n\n"
                            f"- Zora AI Assistant")

                    # Dispatch email
                    send_email_notification(subject, body, recipient_email=email_recipient)

                    # Mark as triggered
                    cursor.execute("UPDATE reminders SET status='triggered' WHERE id=?", (r_id,))
                    conn.commit()
                    logger.info(f"Triggered reminder {r_id} for task '{task}'")

            conn.close()
        except Exception as e:
            logger.error(f"Error in background reminder loop: {e}")

        await asyncio.sleep(30)
