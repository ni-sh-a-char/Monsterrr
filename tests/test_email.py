"""
Test for email sending in scheduler.py
"""

import pytest
from unittest.mock import patch
import scheduler

def test_send_status_report_email():
    with patch("smtplib.SMTP") as mock_smtp:
        scheduler.send_status_report()
        assert mock_smtp.called
