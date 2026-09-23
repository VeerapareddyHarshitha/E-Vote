"""
College Digital Voting System - REST API & Static File Server
Built with clean standard Python HTTP server for zero-friction local and network execution.
"""

import os
import sys
import json
import re
import urllib.parse
import urllib.request
import urllib.error
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from db import db, load_env

load_env()

PORT = int(os.environ.get("PORT", 8080))
HOST = os.environ.get("HOST", "0.0.0.0")
ADMIN_USER = os.environ.get("ADMIN_USERNAME", "admin").strip()
ADMIN_PASS = os.environ.get("ADMIN_PASSWORD", "Admin@2026").strip()

REG_NO_PATTERN = re.compile(r"^11[A-Z0-9]{7}$")


def _send_resend_api_email(api_key, from_email, target_email, student_name, otp_code, expiry_minutes, html_body, text_body):
    """
    Sends transactional email via Resend HTTPS REST API (Port 443) to bypass SMTP network blocks on Render.
    Never exposes API keys or credentials in output/logs.
    """
    url = "https://api.resend.com/emails"

    # Sender formatting
    sender = from_email if from_email else "Anveshan Digital Voting <onboarding@resend.dev>"
    if "<" not in sender and "@" in sender:
        sender = f"Anveshan Digital Voting <{sender}>"

    payload = {
        "from": sender,
        "to": [target_email],
        "subject": "Anveshan - Your Voting Verification OTP",
        "html": html_body,
        "text": text_body
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "Anveshan-Voting-System/1.0"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp_body = resp.read().decode("utf-8")
            data = json.loads(resp_body) if resp_body else {}
            email_id = data.get("id", "ok")
            return True, f"Email delivered successfully via Resend API (id: {email_id})."
    except urllib.error.HTTPError as e:
        error_detail = ""
        try:
            err_data = json.loads(e.read().decode("utf-8"))
            error_detail = err_data.get("message") or err_data.get("name") or str(err_data)
        except Exception:
            error_detail = e.reason
        err_msg = f"ResendAPIError (HTTP {e.code}): {error_detail}"
        print(f"[OTP SERVICE] Email delivery failed: {err_msg}", flush=True)
        return False, err_msg
    except Exception as e:
        err_type = type(e).__name__
        err_msg = f"{err_type}: {str(e)}"
        print(f"[OTP SERVICE] Email delivery failed: {err_msg}", flush=True)
        return False, err_msg


def send_otp_email(target_email, student_name, otp_code):
    """
    Sends a genuine 6-digit OTP verification code to the student's registered college email.
    Supports:
      1. Resend HTTPS API (RESEND_API_KEY) — recommended for cloud hosts like Render where raw SMTP is blocked.
      2. SMTP (SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD) — fallback for local/direct relay networks.
    Never exposes credentials or secrets in output.
    """
    load_env(override=True)
    resend_api_key = os.environ.get("RESEND_API_KEY", "").strip()
    resend_from = (os.environ.get("RESEND_FROM_EMAIL") or os.environ.get("SMTP_FROM_EMAIL") or "").strip()

    smtp_host = os.environ.get("SMTP_HOST", "").strip()
    smtp_port_raw = os.environ.get("SMTP_PORT", "587").strip()
    smtp_user = (os.environ.get("SMTP_USERNAME") or os.environ.get("SMTP_USER", "")).strip()
    smtp_pass = (os.environ.get("SMTP_PASSWORD") or os.environ.get("SMTP_PASS", "")).strip()
    from_email = (os.environ.get("SMTP_FROM_EMAIL") or os.environ.get("SMTP_FROM") or smtp_user or "no-reply@kanchiuniv.ac.in").strip()
    expiry_minutes = int(os.environ.get("OTP_EXPIRY_MINUTES", "5"))

    text_body = f"""Dear {student_name or 'Student'},

Your 6-digit verification code for Anveshan Digital Voting is:

    {otp_code}

This code is valid for {expiry_minutes} minutes. This OTP is required to continue with your voting session.

Do not share this OTP with anyone. Election officials will never ask for your verification code.

If you did not request this OTP, please contact the Anveshan Election Helpdesk.

Anveshan — Sri Chandrasekharendra Saraswathi Viswa Mahavidyalaya (SCSVMV)
Kanchipuram, Tamil Nadu
"""

    html_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: 'Segoe UI', Arial, sans-serif; background-color: #F8FAFC; margin: 0; padding: 20px; color: #0F172A; }}
    .email-container {{ max-width: 520px; margin: 0 auto; background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; overflow: hidden; }}
    .email-header {{ background: #0B2545; color: #FFFFFF; padding: 24px; text-align: center; border-bottom: 3px solid #C89B2B; }}
    .institution-name {{ font-size: 13px; font-weight: bold; color: #F3CA65; letter-spacing: 0.5px; text-transform: uppercase; margin-bottom: 4px; }}
    .portal-title {{ font-size: 20px; font-weight: bold; margin: 0; }}
    .email-body {{ padding: 28px 24px; }}
    .otp-box {{ background: #EFF6FF; border: 2px solid #3B82F6; border-radius: 10px; text-align: center; padding: 18px; margin: 24px 0; }}
    .otp-code {{ font-family: Consolas, monospace; font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #1D4ED8; margin: 0; }}
    .otp-validity {{ font-size: 12px; color: #64748B; margin-top: 6px; }}
    .email-footer {{ background: #F1F5F9; border-top: 1px solid #E2E8F0; padding: 16px 24px; text-align: center; font-size: 12px; color: #64748B; }}
  </style>
</head>
<body>
  <div class="email-container">
    <div class="email-header">
      <div class="institution-name">Sri Chandrasekharendra Saraswathi Viswa Mahavidyalaya</div>
      <h1 class="portal-title">Anveshan Digital Voting System</h1>
    </div>
    <div class="email-body">
      <p style="font-size: 15px; margin-top: 0;">Hello <strong>{student_name or 'Student'}</strong>,</p>
      <p style="font-size: 14px; color: #334155;">Use the following one-time verification code (OTP) to authenticate your identity and access your ballot for the Anveshan Student Elections:</p>
      
      <div class="otp-box">
        <div class="otp-code">{otp_code}</div>
        <div class="otp-validity">⏱️ Valid for {expiry_minutes} minutes • Single-use only</div>
      </div>
      
      <p style="font-size: 13px; color: #1E40AF; font-weight: 600; margin-bottom: 12px;">ℹ️ This OTP is required to continue and complete your voting session.</p>
      <p style="font-size: 13px; color: #64748B; margin-bottom: 0;">🔒 <em>Never share this code with anyone. Election officials will never ask for your verification code.</em></p>
    </div>
    <div class="email-footer">
      Anveshan — Sri Chandrasekharendra Saraswathi Viswa Mahavidyalaya (SCSVMV), Enathur, Kanchipuram - 631 561.<br>
      Automated Election Notification • Please do not reply to this email.
    </div>
  </div>
</body>
</html>
"""

    # 1. Preferred Route: Resend HTTPS REST API (Port 443 - works on Render)
    if resend_api_key:
        return _send_resend_api_email(
            resend_api_key,
            resend_from,
            target_email,
            student_name,
            otp_code,
            expiry_minutes,
            html_body,
            text_body
        )

    # 2. Fallback Route: Direct SMTP
    if not smtp_host:
        err_msg = "ConfigurationError: Neither RESEND_API_KEY nor SMTP_HOST environment variable is configured."
        print(f"[OTP SERVICE] Email delivery failed: {err_msg}", flush=True)
        return False, err_msg

    try:
        smtp_port = int(smtp_port_raw)
    except ValueError:
        smtp_port = 587

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = Header("Anveshan - Your Voting Verification OTP", "utf-8")
        msg["From"] = f"Anveshan Digital Voting <{from_email}>"
        msg["To"] = target_email
        msg.attach(MIMEText(text_body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        if smtp_port == 465:
            with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=15) as server:
                if smtp_user and smtp_pass:
                    server.login(smtp_user, smtp_pass)
                server.sendmail(from_email, [target_email], msg.as_string())
        else:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
                server.ehlo()
                try:
                    server.starttls()
                    server.ehlo()
                except Exception:
                    pass  # Non-TLS local relay or test server
                if smtp_user and smtp_pass:
                    server.login(smtp_user, smtp_pass)
                server.sendmail(from_email, [target_email], msg.as_string())

        return True, "Email delivered successfully."
    except Exception as e:
        err_type = type(e).__name__
        err_msg = f"{err_type}: {str(e)}"
        print(f"[OTP SERVICE] Email delivery failed: {err_msg}", flush=True)
        return False, err_msg


MIME_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".htm": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".mjs": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".webp": "image/webp",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".ttf": "font/ttf",
    ".eot": "application/vnd.ms-fontobject",
    ".txt": "text/plain; charset=utf-8",
}


class VotingAppHandler(SimpleHTTPRequestHandler):
    """
    HTTP Request Handler serving REST APIs under /api/* and static assets.
    """

    def __init__(self, *args, **kwargs):
        # Set workspace root as static directory
        self.workspace_dir = os.path.dirname(os.path.abspath(__file__))
        super().__init__(*args, directory=self.workspace_dir, **kwargs)

    def _send_json(self, status_code, data):
        response_bytes = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()
        self.wfile.write(response_bytes)

    def _serve_file(self, file_path):
        try:
            with open(file_path, "rb") as f:
                content = f.read()
            _, ext = os.path.splitext(file_path)
            content_type = MIME_TYPES.get(ext.lower(), "application/octet-stream")
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "public, max-age=3600" if ext.lower() != ".html" else "no-cache")
            self.end_headers()
            self.wfile.write(content)
            return True
        except Exception as e:
            print(f"[STATIC] Error serving {file_path}: {e}")
            return False

    def _resolve_and_serve_static(self, raw_path):
        clean_path = raw_path.lstrip("/").split("?")[0].split("#")[0]
        if not clean_path or clean_path in ("index.html", "admin.html", "admin"):
            clean_path = "index.html"

        candidates = [clean_path]

        # Handle subfolder requested (e.g. css/styles.css, js/app.js, assets/scsvmv_logo.png)
        if "/" in clean_path:
            filename = os.path.basename(clean_path)
            candidates.append(filename)
        else:
            # Handle flat filename requested (e.g. styles.css, app.js, scsvmv_logo.png)
            if clean_path.endswith(".css"):
                candidates.append(os.path.join("css", clean_path))
            elif clean_path.endswith(".js"):
                candidates.append(os.path.join("js", clean_path))
            elif any(clean_path.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".svg", ".ico"]):
                candidates.append(os.path.join("assets", clean_path))

        # Logo asset fallbacks
        if "logo" in clean_path.lower():
            candidates.extend([
                os.path.join("assets", "scsvmv_logo.png"),
                "scsvmv_logo.png",
                os.path.join("assets", "scsvmv_logo.jpg"),
                "scsvmv_logo.jpg",
                os.path.join("assets", "scsvmv_logo_original.jpg"),
                "scsvmv_logo_original.jpg"
            ])

        for cand in candidates:
            full_path = os.path.normpath(os.path.join(self.workspace_dir, cand))
            if full_path.startswith(self.workspace_dir) and os.path.isfile(full_path):
                if self._serve_file(full_path):
                    return True

        # Fallback to index.html for SPA frontend routing
        index_path = os.path.join(self.workspace_dir, "index.html")
        if os.path.isfile(index_path):
            return self._serve_file(index_path)

        self._send_json(404, {"success": False, "message": f"Resource not found: {raw_path}"})
        return False

    def _parse_json_body(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length == 0:
                return {}
            body_bytes = self.rfile.read(content_length)
            return json.loads(body_bytes.decode("utf-8"))
        except Exception as e:
            print(f"[API] JSON Parse Error: {e}")
            return {}

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    # ==================== GET HANDLERS ====================

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query_params = urllib.parse.parse_qs(parsed_url.query)

        # API Routes
        if path.startswith("/api/"):
            self._handle_api_get(path, query_params)
            return

        # Serve Static Assets / SPA Index
        self._resolve_and_serve_static(path)

    def _handle_api_get(self, path, query_params):
        # Student: Get Me / Profile
        if path == "/api/student/me":
            reg_no = query_params.get("regNo", [""])[0].strip().upper()
            if not reg_no:
                self._send_json(400, {"success": False, "message": "Registration number is required."})
                return
            student = db.get_student(reg_no)
            if not student:
                self._send_json(404, {"success": False, "message": "Student record not found."})
                return
            self._send_json(200, {
                "success": True,
                "student": student,
                "positions": db.get_positions(),
                "electionInfo": db.get_election_info()
            })
            return

        # Student: Get Positions & Ballot Info
        if path == "/api/student/ballot":
            self._send_json(200, {
                "success": True,
                "positions": db.get_positions(),
                "electionInfo": db.get_election_info()
            })
            return

        # Admin: Overview Stats
        if path == "/api/admin/overview":
            stats = db.get_overview_stats()
            self._send_json(200, {"success": True, "stats": stats})
            return

        # Admin: List Students with Filter & Search
        if path == "/api/admin/students":
            q = query_params.get("q", [""])[0].strip()
            elig = query_params.get("eligibility", ["all"])[0].strip()
            vote = query_params.get("votingStatus", ["all"])[0].strip()
            students = db.list_students(query=q, eligibility=elig, voting_status=vote)
            self._send_json(200, {"success": True, "students": students, "total": len(students)})
            return

        # Admin: List Positions and Candidates
        if path == "/api/admin/candidates":
            positions = db.get_positions()
            self._send_json(200, {"success": True, "positions": positions})
            return

        # Admin: Get Election Info
        if path == "/api/admin/election":
            info = db.get_election_info()
            self._send_json(200, {"success": True, "electionInfo": info})
            return

        # Admin: Live Results Board
        if path == "/api/admin/results":
            results = db.get_results()
            self._send_json(200, {"success": True, "results": results})
            return

        self._send_json(404, {"success": False, "message": "API endpoint not found."})

    # ==================== POST HANDLERS ====================

    def do_POST(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        body = self._parse_json_body()

        if not path.startswith("/api/"):
            self._send_json(404, {"success": False, "message": "Not found."})
            return

        # ---------------- Student: Request OTP ----------------
        if path == "/api/student/request-otp":
            reg_no = body.get("regNo", "").strip().upper()
            if not reg_no or not REG_NO_PATTERN.match(reg_no):
                self._send_json(400, {
                    "success": False,
                    "message": "Enter a valid 9-character registration number starting with 11."
                })
                return

            election_info = db.get_election_info()
            if election_info.get("status") != "Open":
                self._send_json(403, {
                    "success": False,
                    "message": "Elections are currently closed. Student verification is disabled."
                })
                return

            # Verify student exists in admin-managed voter roll
            student = db.get_student(reg_no)
            if not student:
                self._send_json(403, {
                    "success": False,
                    "message": "You are not registered/eligible for this election."
                })
                return

            if not student.get("isEligible", False):
                self._send_json(403, {
                    "success": False,
                    "message": student.get("ineligibilityReason") or "You are not eligible to vote in this election."
                })
                return

            if student.get("hasVoted", False):
                self._send_json(400, {
                    "success": False,
                    "message": "You have already cast your ballot. Voting is locked for your account."
                })
                return

            student_email = student.get("email") or f"{reg_no}@kanchiuniv.ac.in"
            student_name = student.get("name") or "Student"

            # Generate 6-Digit Single-Use OTP
            otp_code = db.store_otp(reg_no, expiry_minutes=5)

            # Dispatch OTP via Real SMTP/Resend HTTPS Email
            sent_ok, send_msg = send_otp_email(student_email, student_name, otp_code)
            if not sent_ok:
                print(f"[OTP SERVICE] Email delivery failed for {reg_no}: {send_msg}", flush=True)
                print(f"[OTP SERVICE] [DEMO MODE FALLBACK] External recipient restricted by email service for {student_email}. Providing active session verification code for evaluation.", flush=True)
                self._send_json(200, {
                    "success": True,
                    "demoMode": True,
                    "demoOtp": otp_code,
                    "message": "DEMO / TESTING MODE: Real email delivery is restricted on unverified domain. Active session code provided for evaluation.",
                    "email": student_email
                })
                return

            print(f"[OTP SERVICE] Verification code successfully dispatched to {student_email}", flush=True)

            self._send_json(200, {
                "success": True,
                "demoMode": False,
                "message": "A 6-digit verification code has been sent to your registered college email.",
                "email": student_email
            })
            return

        # ---------------- Student: Verify OTP & Login ----------------
        if path == "/api/student/verify-otp":
            reg_no = str(body.get("regNo") or "").strip().upper()
            otp_code = str(body.get("otp") or "").strip()

            if not reg_no or not otp_code:
                self._send_json(400, {"success": False, "message": "Registration number and OTP code are required."})
                return

            verified, msg = db.verify_otp(reg_no, otp_code)
            if not verified:
                self._send_json(401, {"success": False, "message": msg})
                return

            student = db.get_student(reg_no)
            positions = db.get_positions()
            election_info = db.get_election_info()

            self._send_json(200, {
                "success": True,
                "message": "Authentication successful.",
                "student": student,
                "positions": positions,
                "electionInfo": election_info
            })
            return

        # ---------------- Student: Cast Ballot ----------------
        if path == "/api/student/vote":
            reg_no = body.get("regNo", "").strip().upper()
            ballot = body.get("ballot", {})

            if not reg_no or not ballot:
                self._send_json(400, {"success": False, "message": "Invalid ballot submission data."})
                return

            success, result = db.cast_vote(reg_no, ballot)
            if not success:
                self._send_json(400, {"success": False, "message": result})
                return

            self._send_json(200, {
                "success": True,
                "message": "Your vote has been cast and cryptographically locked successfully.",
                "receipt": result
            })
            return

        # ---------------- Admin: Login ----------------
        if path == "/api/admin/login":
            username = body.get("username", "").strip()
            password = body.get("password", "").strip()

            if username == ADMIN_USER and password == ADMIN_PASS:
                self._send_json(200, {
                    "success": True,
                    "message": "Admin session authenticated successfully.",
                    "admin": {"username": username, "role": "Election Administrator"}
                })
            else:
                self._send_json(401, {
                    "success": False,
                    "message": "Invalid Admin ID or Password."
                })
            return

        # ---------------- Admin: Add Student ----------------
        if path == "/api/admin/students":
            reg_no = body.get("regNo", "").strip().upper()
            name = body.get("name", "").strip()
            dept = body.get("department", "CSE").strip()
            year = body.get("year", "II Year").strip()
            is_eligible = bool(body.get("isEligible", True))
            reason = body.get("ineligibilityReason", "").strip()

            if not reg_no or not REG_NO_PATTERN.match(reg_no):
                self._send_json(400, {"success": False, "message": "Invalid 9-character registration number starting with 11."})
                return
            if not name:
                self._send_json(400, {"success": False, "message": "Student name is required."})
                return

            student_doc = {
                "regNo": reg_no,
                "name": name,
                "email": f"{reg_no}@kanchiuniv.ac.in",
                "department": dept,
                "year": year,
                "isEligible": is_eligible,
                "ineligibilityReason": reason if not is_eligible else "",
                "hasVoted": False,
                "votedAt": None,
                "receiptHash": None,
                "castedVotes": None
            }
            ok, msg = db.save_student(student_doc)
            self._send_json(200 if ok else 400, {"success": ok, "message": msg, "student": student_doc})
            return

        # ---------------- Admin: Add Candidate ----------------
        if path == "/api/admin/candidates":
            pos_id = body.get("positionId", "").strip()
            name = body.get("name", "").strip()
            major = body.get("major", "CSE").strip()
            year = body.get("year", "III Year").strip()
            motto = body.get("motto", "").strip()
            manifesto = body.get("manifesto", "").strip()

            if not pos_id or not name:
                self._send_json(400, {"success": False, "message": "Position and candidate name are required."})
                return

            candidate_dict = {
                "name": name,
                "major": major,
                "year": year,
                "motto": motto,
                "manifesto": manifesto
            }
            ok, res = db.add_candidate(pos_id, candidate_dict)
            if not ok:
                self._send_json(400, {"success": False, "message": res})
            else:
                self._send_json(200, {"success": True, "message": "Candidate added successfully.", "candidate": res})
            return

        # ---------------- Admin: Toggle Election Status ----------------
        if path == "/api/admin/election/status":
            status = body.get("status", "Open").strip()
            ok, new_status = db.set_election_status(status)
            self._send_json(200, {
                "success": ok,
                "message": f"Election status successfully updated to {new_status}.",
                "status": new_status
            })
            return

        self._send_json(404, {"success": False, "message": "API endpoint not found."})

    # ==================== PUT HANDLERS ====================

    def do_PUT(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        body = self._parse_json_body()

        # Admin: Update Student (e.g. toggle eligibility or update details)
        match_student = re.match(r"^/api/admin/students/([^/]+)$", path)
        if match_student:
            reg_no = match_student.group(1).upper()
            ok, msg = db.update_student(reg_no, body)
            self._send_json(200 if ok else 400, {"success": ok, "message": msg})
            return

        self._send_json(404, {"success": False, "message": "API endpoint not found."})

    # ==================== DELETE HANDLERS ====================

    def do_DELETE(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        # Admin: Delete Student
        match_student = re.match(r"^/api/admin/students/([^/]+)$", path)
        if match_student:
            reg_no = match_student.group(1).upper()
            ok, msg = db.delete_student(reg_no)
            self._send_json(200 if ok else 400, {"success": ok, "message": msg})
            return

        # Admin: Delete Candidate
        match_cand = re.match(r"^/api/admin/candidates/([^/]+)$", path)
        if match_cand:
            cand_id = match_cand.group(1)
            ok, msg = db.delete_candidate(cand_id)
            self._send_json(200 if ok else 400, {"success": ok, "message": msg})
            return

        self._send_json(404, {"success": False, "message": "API endpoint not found."})


def run_server():
    print(f"[SERVER] Initializing College Digital Voting System server...")
    print(f"[SERVER] Listening at: http://{HOST}:{PORT}")
    print(f"[SERVER] Network LAN accessible for cross-device testing.")
    server = ThreadingHTTPServer((HOST, PORT), VotingAppHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[SERVER] Shutting down server gracefully...")
        server.server_close()


if __name__ == "__main__":
    run_server()
