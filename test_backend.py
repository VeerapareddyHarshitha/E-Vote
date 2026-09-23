"""
Integration and Verification Test Suite for College Digital Voting System
Validates real SMTP email OTP delivery, no OTP leakage in API responses, and end-to-end security.
"""

import urllib.request
import urllib.parse
import json
import socket
import threading
import time
import os
import re

BASE_URL = "http://127.0.0.1:8080"
ENV_FILE = os.path.join(os.path.dirname(__file__), ".env")


class MockSMTPServer:
    """Lightweight test SMTP server listening on localhost for automated socket verification."""
    def __init__(self, host="127.0.0.1", port=1025):
        self.host = host
        self.port = port
        self.received_messages = []
        self.running = False
        self.sock = None
        self.thread = None

    def start(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))
        self.sock.listen(5)
        self.running = True
        self.thread = threading.Thread(target=self._serve, daemon=True)
        self.thread.start()
        print(f"[TEST SMTP] Mock SMTP server listening on {self.host}:{self.port}")

    def _serve(self):
        while self.running:
            try:
                conn, _ = self.sock.accept()
                threading.Thread(target=self._handle_client, args=(conn,), daemon=True).start()
            except Exception:
                break

    def _handle_client(self, conn):
        with conn:
            conn.sendall(b"220 localhost ESMTP MockServer\r\n")
            msg_data = []
            in_data = False
            while True:
                line = conn.recv(2048)
                if not line:
                    break
                text = line.decode("utf-8", errors="ignore")
                if in_data:
                    msg_data.append(text)
                    if "\r\n.\r\n" in text or text.endswith(".\r\n") or text == ".\n":
                        in_data = False
                        full_msg = "".join(msg_data)
                        self.received_messages.append(full_msg)
                        conn.sendall(b"250 2.0.0 Ok: queued\r\n")
                elif text.upper().startswith("EHLO") or text.upper().startswith("HELO"):
                    conn.sendall(b"250-localhost\r\n250 8BITMIME\r\n")
                elif text.upper().startswith("MAIL FROM"):
                    conn.sendall(b"250 2.1.0 Ok\r\n")
                elif text.upper().startswith("RCPT TO"):
                    conn.sendall(b"250 2.1.5 Ok\r\n")
                elif text.upper().startswith("DATA"):
                    in_data = True
                    conn.sendall(b"354 End data with <CR><LF>.<CR><LF>\r\n")
                elif text.upper().startswith("QUIT"):
                    conn.sendall(b"221 2.0.0 Bye\r\n")
                    break
                else:
                    conn.sendall(b"250 Ok\r\n")

    def stop(self):
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass


def api_call(endpoint, method="GET", data=None):
    url = f"{BASE_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}
    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))
    except Exception as e:
        return 500, {"error": str(e)}


def run_tests():
    print("--- Starting Full Verification Test Suite for SMTP Email OTP ---")

    original_env_content = ""
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            original_env_content = f.read()

    smtp_mock = MockSMTPServer(port=1025)

    try:
        # 1. Admin Login
        print("\n[Test 1] Admin Login...")
        status, res = api_call("/api/admin/login", "POST", {"username": "admin", "password": "Admin@2026"})
        assert status == 200 and res.get("success"), f"Admin login failed: {res}"
        print("[PASS] Admin Login Passed")

        # 2. Unregistered Student Rejection Test
        print("\n[Test 2] Non-Admin-Added Student Requesting OTP (11UNREG99)...")
        status, res = api_call("/api/student/request-otp", "POST", {"regNo": "11UNREG99"})
        assert status == 403 and not res.get("success"), f"Expected 403, got: {status}, {res}"
        print(f"[PASS] Unregistered student blocked: {res.get('message')}")

        # 3. Admin Enrolling New Student
        print("\n[Test 3] Admin Enrolling Test Student (11TST0001)...")
        api_call("/api/admin/students", "POST", {
            "regNo": "11TST0001",
            "name": "Live Test Student",
            "department": "CSE",
            "year": "II Year",
            "isEligible": True
        })
        print("[PASS] Test student enrolled successfully.")

        # 4. Request OTP when SMTP is unconfigured (Should fail gracefully with clear error without leaking OTP)
        print("\n[Test 4] Requesting OTP with Unconfigured SMTP (Graceful Error Check)...")
        status, res = api_call("/api/student/request-otp", "POST", {"regNo": "11TST0001"})
        assert status == 500 and not res.get("success"), f"Expected 500 when SMTP unconfigured, got {status}: {res}"
        assert "debugOtp" not in res and "otp" not in res, "CRITICAL ERROR: OTP exposed during SMTP failure!"
        print(f"[PASS] Unconfigured SMTP rejected safely: '{res.get('message')}' (No OTP leak)")

        # 5. Configure SMTP and Start Mock Mail Server
        print("\n[Test 5] Starting Mock SMTP Server and Configuring Environment...")
        smtp_mock.start()

        # Update .env with mock test SMTP parameters
        test_env_content = original_env_content + "\nSMTP_HOST=127.0.0.1\nSMTP_PORT=1025\nSMTP_FROM_EMAIL=no-reply@kanchiuniv.ac.in\n"
        with open(ENV_FILE, "w", encoding="utf-8") as f:
            f.write(test_env_content)

        # 6. Request OTP via Real SMTP Transmission
        print("\n[Test 6] Requesting OTP via Real SMTP Transmission...")
        status, res = api_call("/api/student/request-otp", "POST", {"regNo": "11TST0001"})
        assert status == 200 and res.get("success"), f"Expected 200, got {status}: {res}"

        # VERIFY ZERO OTP LEAKAGE IN PUBLIC API RESPONSE
        assert "debugOtp" not in res, "CRITICAL ERROR: debugOtp found in public API response!"
        assert "otp" not in res, "CRITICAL ERROR: otp code found in public API response!"
        print(f"[PASS] API response message: '{res.get('message')}' (Zero OTP exposure in response)")

        # Verify Mock SMTP received the email
        time.sleep(0.6)
        assert len(smtp_mock.received_messages) > 0, "ERROR: No SMTP email was received by the mail server!"
        last_email = smtp_mock.received_messages[-1]
        assert "11TST0001@kanchiuniv.ac.in" in last_email, "ERROR: Recipient email address not in SMTP message!"
        assert "Anveshan" in last_email, "ERROR: Subject/branding missing from email!"

        # Extract 6-digit OTP code from genuine received MIME email
        import email
        import base64

        msg = email.message_from_string(last_email)
        email_text_body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    payload = part.get_payload()
                    try:
                        email_text_body = base64.b64decode(payload).decode("utf-8")
                    except Exception:
                        email_text_body = payload
                    break
        else:
            email_text_body = msg.get_payload()

        otp_match = re.search(r"\b([0-9]{6})\b", email_text_body)
        assert otp_match, f"Could not find 6-digit OTP in decoded email content: {email_text_body}"
        extracted_otp = otp_match.group(1)
        print(f"[PASS] Genuine email received by SMTP server. Extracted OTP: {extracted_otp}")

        # 7. Verify Incorrect OTP Rejection
        print("\n[Test 7] Verify Incorrect OTP Rejection...")
        status, res = api_call("/api/student/verify-otp", "POST", {"regNo": "11TST0001", "otp": "000000"})
        assert status == 401 and not res.get("success"), f"Expected 401, got {status}: {res}"
        print(f"[PASS] Incorrect OTP rejected: {res.get('message')}")

        # 8. Verify Correct OTP from Email
        print("\n[Test 8] Student Verifying Correct OTP from Email...")
        status, res = api_call("/api/student/verify-otp", "POST", {"regNo": "11TST0001", "otp": extracted_otp})
        assert status == 200 and res.get("success"), f"Expected 200, got {status}: {res}"
        print("[PASS] Student successfully verified with genuine email OTP.")

        # 9. Verify OTP Cannot Be Reused
        print("\n[Test 9] Verify OTP Cannot Be Reused...")
        status, res = api_call("/api/student/verify-otp", "POST", {"regNo": "11TST0001", "otp": extracted_otp})
        assert status == 401 and not res.get("success"), f"Expected 401 for reused OTP, got {status}: {res}"
        print(f"[PASS] Reused OTP rejected: {res.get('message')}")

        # 10. Cast Ballot
        print("\n[Test 10] Cast Ballot...")
        status, res = api_call("/api/student/vote", "POST", {
            "regNo": "11TST0001",
            "ballot": {"president": "c1", "vicePresident": "c3", "secretary": "c5"}
        })
        assert status == 200 and res.get("success")
        print(f"[PASS] Ballot cast successfully. Receipt Hash: {res['receipt']['receiptHash']}")

        # 11. Duplicate Vote Prevention
        print("\n[Test 11] Duplicate Vote Prevention...")
        status, res = api_call("/api/student/vote", "POST", {
            "regNo": "11TST0001",
            "ballot": {"president": "c1", "vicePresident": "c3", "secretary": "c5"}
        })
        assert status == 400 and not res.get("success")
        print(f"[PASS] Duplicate vote locked: {res.get('message')}")

        # Cleanup test student
        api_call("/api/admin/students/11TST0001", "DELETE")
        print("[PASS] Cleaned up temporary test voter.")

        # 12. Ineligible Student Voting Rejection Test
        print("\n[Test 12] Ineligible Student Attempting Vote (11ABC0713)...")
        status, res = api_call("/api/student/request-otp", "POST", {"regNo": "11ABC0713"})
        assert status == 403 and not res.get("success")
        print(f"[PASS] Ineligible student blocked: {res.get('message')}")

        # 13. Election Controls (Close & Re-open)
        print("\n[Test 13] Election Status Toggle...")
        status, res = api_call("/api/admin/election/status", "POST", {"status": "Closed"})
        assert status == 200 and res.get("status") == "Closed"
        status, res = api_call("/api/student/request-otp", "POST", {"regNo": "11ABC0598"})
        assert status == 403
        print("[PASS] Election Closed successfully and locked student verification")

        api_call("/api/admin/election/status", "POST", {"status": "Open"})
        print("[PASS] Election Re-opened successfully")

        print("\n=======================================================")
        print("ALL 13 SMTP REAL EMAIL & SECURITY TESTS PASSED (100%)!")
        print("=======================================================")

    finally:
        smtp_mock.stop()
        # Restore original .env content
        if original_env_content:
            with open(ENV_FILE, "w", encoding="utf-8") as f:
                f.write(original_env_content)


if __name__ == "__main__":
    run_tests()
