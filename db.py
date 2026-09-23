"""
College Digital Voting System - Modular Database Manager
Supports MongoDB Atlas with automatic fallback to a local document store.
"""

import os
import json
import time
import hashlib
import secrets
from datetime import datetime, timedelta

# Simple environment variable loader if python-dotenv is not installed
def load_env(env_path=".env", override=False):
    if not os.path.exists(env_path):
        return
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip("'").strip('"')
                    if override or k not in os.environ:
                        os.environ[k] = v
    except Exception as e:
        print(f"[ENV] Notice: Could not read .env: {e}")

load_env()

# Default Seed Data for clean initialization
DEFAULT_STUDENTS = {
    "11ABC0425": {
        "regNo": "11ABC0425",
        "name": "V. Harshitha",
        "email": "11ABC0425@kanchiuniv.ac.in",
        "department": "CSE",
        "year": "II Year",
        "isEligible": True,
        "ineligibilityReason": "",
        "hasVoted": False,
        "votedAt": None,
        "receiptHash": None,
        "castedVotes": None
    },
    "11ABC0437": {
        "regNo": "11ABC0437",
        "name": "Y. Abhiram",
        "email": "11ABC0437@kanchiuniv.ac.in",
        "department": "CSE",
        "year": "II Year",
        "isEligible": True,
        "ineligibilityReason": "",
        "hasVoted": True,
        "votedAt": "2026-08-12 10:45 AM",
        "receiptHash": "0x8f9a2b4c1e3d7a6b5c4d3e2f1a0b9c8d7e6f5a4b",
        "castedVotes": {
            "president": "c1",
            "vicePresident": "c3",
            "secretary": "c5"
        }
    },
    "11ABC0459": {
        "regNo": "11ABC0459",
        "name": "N. Sanjana",
        "email": "11ABC0459@kanchiuniv.ac.in",
        "department": "CSE",
        "year": "II Year",
        "isEligible": False,
        "ineligibilityReason": "Not eligible for this election.",
        "hasVoted": False,
        "votedAt": None,
        "receiptHash": None,
        "castedVotes": None
    }
}

DEFAULT_POSITIONS = [
    {
        "id": "president",
        "title": "Student Body President",
        "description": "Leads the Executive Board, represents students before the Board of Trustees, and oversees SGA budget allocation.",
        "candidates": [
            {
                "id": "c1",
                "name": "G. Prameela",
                "major": "CSE",
                "year": "IV Year",
                "motto": "Transparency, Tech Integration & 24/7 Library Access",
                "manifesto": "Pledges to digitize all SGA funding requests, expand 24-hour campus study spaces, and implement renewable energy on student buildings.",
                "votesCount": 0
            },
            {
                "id": "c2",
                "name": "V. Narasimha Reddy",
                "major": "CSE",
                "year": "IV Year",
                "motto": "Empowering Student Entrepreneurship & Career Opportunities",
                "manifesto": "Focusing on doubling annual campus recruitment drives, launching a $50k student startup grant, and revamping dining hall options.",
                "votesCount": 0
            }
        ]
    },
    {
        "id": "vicePresident",
        "title": "Vice President of Student Affairs",
        "description": "Coordinates campus organizations, oversees student wellness programs, and manages inter-departmental committees.",
        "candidates": [
            {
                "id": "c3",
                "name": "B. Murali",
                "major": "CSE",
                "year": "III Year",
                "motto": "Mental Health First & Inclusive Campus Transit",
                "manifesto": "Advocating for 24/7 mental wellness counseling sessions, free campus shuttle tracking app, and peer-to-peer tutoring grants.",
                "votesCount": 0
            },
            {
                "id": "c4",
                "name": "G. Hasini",
                "major": "CSE",
                "year": "III Year",
                "motto": "Affordable Housing & Upgraded Laboratory Facilities",
                "manifesto": "Working to establish student rent subsidies near campus, modernizing computer labs, and extending recreation center hours.",
                "votesCount": 0
            }
        ]
    },
    {
        "id": "secretary",
        "title": "Cultural & Sports Secretary",
        "description": "Directs university tech-fests, cultural galas, intramural tournaments, and student club endowments.",
        "candidates": [
            {
                "id": "c5",
                "name": "B. Kavya Darshini",
                "major": "CSE",
                "year": "III Year",
                "motto": "Fostering Diversity, Creative Arts & Global TechFest",
                "manifesto": "Launching the Annual National Inter-College Innovation Summit, increasing funding for arts & music clubs by 30%.",
                "votesCount": 0
            },
            {
                "id": "c6",
                "name": "M. Yasasri",
                "major": "CSE",
                "year": "III Year",
                "motto": "State-of-the-Art Sports Complex & E-Sports Arena",
                "manifesto": "Upgrading university gym facilities, creating an official collegiate E-sports league, and hosting inter-university leagues.",
                "votesCount": 0
            }
        ]
    }
]

DEFAULT_ELECTION_INFO = {
    "title": "Student Government Association General Election 2026",
    "academicYear": "2025-2026 Academic Session",
    "votingEnds": "2026-09-30T23:59:59",
    "encryptionStandard": "AES-256-GCM Cryptographic Ledger",
    "status": "Open"
}


class DatabaseManager:
    """
    Database interface with support for MongoDB Atlas and clean local fallback.
    """

    def __init__(self):
        self.use_mongodb = False
        self.mongo_client = None
        self.mongo_db = None
        self.local_file_path = os.path.join(os.path.dirname(__file__), "data", "voting_store.json")
        self._init_connection()

    def _init_connection(self):
        mongodb_uri = os.environ.get("MONGODB_URI", "").strip()
        db_name = os.environ.get("DB_NAME", "college_voting_system").strip()

        if mongodb_uri:
            try:
                import pymongo
                print(f"[DB] Connecting to MongoDB Atlas ({db_name})...")
                self.mongo_client = pymongo.MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
                self.mongo_client.server_info() # Validate connection
                self.mongo_db = self.mongo_client[db_name]
                self.use_mongodb = True
                print("[DB] ✓ Successfully connected to MongoDB Atlas!")
                self._seed_mongodb_if_empty()
                return
            except Exception as e:
                print(f"[DB] Notice: MongoDB Atlas connection failed ({e}). Falling back to local store.")
                self.use_mongodb = False

        print("[DB] Using local JSON document store (Modular fallback).")
        self._init_local_store()

    def _init_local_store(self):
        os.makedirs(os.path.dirname(self.local_file_path), exist_ok=True)
        if not os.path.exists(self.local_file_path):
            initial_data = {
                "students": DEFAULT_STUDENTS,
                "positions": DEFAULT_POSITIONS,
                "electionInfo": DEFAULT_ELECTION_INFO,
                "otps": {}
            }
            self._write_local_store(initial_data)

    def _read_local_store(self):
        self._init_local_store()
        try:
            with open(self.local_file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[DB] Error reading local store: {e}")
            return {
                "students": DEFAULT_STUDENTS,
                "positions": DEFAULT_POSITIONS,
                "electionInfo": DEFAULT_ELECTION_INFO,
                "otps": {}
            }

    def _write_local_store(self, data):
        os.makedirs(os.path.dirname(self.local_file_path), exist_ok=True)
        with open(self.local_file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _seed_mongodb_if_empty(self):
        if not self.use_mongodb or self.mongo_db is None:
            return
        try:
            if self.mongo_db.students.count_documents({}) == 0:
                print("[DB] Seeding MongoDB students collection...")
                for reg_no, doc in DEFAULT_STUDENTS.items():
                    doc_copy = dict(doc)
                    doc_copy["_id"] = reg_no
                    self.mongo_db.students.insert_one(doc_copy)

            if self.mongo_db.positions.count_documents({}) == 0:
                print("[DB] Seeding MongoDB positions collection...")
                for pos in DEFAULT_POSITIONS:
                    pos_copy = dict(pos)
                    pos_copy["_id"] = pos["id"]
                    self.mongo_db.positions.insert_one(pos_copy)

            if self.mongo_db.election_info.count_documents({}) == 0:
                print("[DB] Seeding MongoDB election_info collection...")
                info_copy = dict(DEFAULT_ELECTION_INFO)
                info_copy["_id"] = "current"
                self.mongo_db.election_info.insert_one(info_copy)
        except Exception as e:
            print(f"[DB] Error seeding MongoDB: {e}")

    # ==================== STUDENT OPERATIONS ====================

    def get_student(self, reg_no):
        reg_no = (reg_no or "").strip().toUpperCase() if hasattr(reg_no, "toUpperCase") else (reg_no or "").strip().upper()
        if self.use_mongodb:
            doc = self.mongo_db.students.find_one({"_id": reg_no})
            if doc:
                doc.pop("_id", None)
                return doc
            return None
        else:
            store = self._read_local_store()
            return store.get("students", {}).get(reg_no)

    def list_students(self, query=None, eligibility=None, voting_status=None):
        if self.use_mongodb:
            filter_q = {}
            if eligibility == "eligible":
                filter_q["isEligible"] = True
            elif eligibility == "ineligible":
                filter_q["isEligible"] = False

            if voting_status == "voted":
                filter_q["hasVoted"] = True
            elif voting_status == "notvoted":
                filter_q["hasVoted"] = False

            docs = list(self.mongo_db.students.find(filter_q))
            students = []
            clean_q = (query or "").strip().lower()
            for d in docs:
                d.pop("_id", None)
                if clean_q:
                    if clean_q not in d.get("name", "").lower() and clean_q not in d.get("regNo", "").lower():
                        continue
                students.append(d)
            return students
        else:
            store = self._read_local_store()
            students = list(store.get("students", {}).values())
            clean_q = (query or "").strip().lower()
            filtered = []
            for s in students:
                if eligibility == "eligible" and not s.get("isEligible"):
                    continue
                if eligibility == "ineligible" and s.get("isEligible"):
                    continue
                if voting_status == "voted" and not s.get("hasVoted"):
                    continue
                if voting_status == "notvoted" and s.get("hasVoted"):
                    continue
                if clean_q:
                    if clean_q not in s.get("name", "").lower() and clean_q not in s.get("regNo", "").lower():
                        continue
                filtered.append(s)
            return filtered

    def save_student(self, student_dict):
        reg_no = student_dict.get("regNo", "").strip().upper()
        if not reg_no:
            return False, "Registration number is required."

        student_dict["regNo"] = reg_no
        student_dict["email"] = f"{reg_no}@kanchiuniv.ac.in"

        if self.use_mongodb:
            doc_copy = dict(student_dict)
            doc_copy["_id"] = reg_no
            self.mongo_db.students.update_one({"_id": reg_no}, {"$set": doc_copy}, upsert=True)
            return True, "Student saved successfully."
        else:
            store = self._read_local_store()
            store.setdefault("students", {})[reg_no] = student_dict
            self._write_local_store(store)
            return True, "Student saved successfully."

    def update_student(self, reg_no, update_data):
        reg_no = reg_no.strip().upper()
        if self.use_mongodb:
            res = self.mongo_db.students.update_one({"_id": reg_no}, {"$set": update_data})
            if res.matched_count == 0:
                return False, "Student not found."
            return True, "Student updated successfully."
        else:
            store = self._read_local_store()
            if reg_no not in store.get("students", {}):
                return False, "Student not found."
            store["students"][reg_no].update(update_data)
            self._write_local_store(store)
            return True, "Student updated successfully."

    def delete_student(self, reg_no):
        reg_no = reg_no.strip().upper()
        if self.use_mongodb:
            res = self.mongo_db.students.delete_one({"_id": reg_no})
            if res.deleted_count == 0:
                return False, "Student not found."
            return True, "Student deleted successfully."
        else:
            store = self._read_local_store()
            if reg_no in store.get("students", {}):
                del store["students"][reg_no]
                self._write_local_store(store)
                return True, "Student deleted successfully."
            return False, "Student not found."

    # ==================== POSITIONS & CANDIDATES ====================

    def get_positions(self):
        if self.use_mongodb:
            docs = list(self.mongo_db.positions.find({}))
            for d in docs:
                d.pop("_id", None)
            return docs
        else:
            store = self._read_local_store()
            return store.get("positions", [])

    def add_candidate(self, position_id, candidate_dict):
        pos_id = position_id.strip()
        name = candidate_dict.get("name", "").strip()
        if not name:
            return False, "Candidate name is required."

        if self.use_mongodb:
            # Generate next ID (e.g. c7)
            positions = list(self.mongo_db.positions.find({}))
            all_ids = []
            for p in positions:
                for c in p.get("candidates", []):
                    cid = c.get("id", "")
                    if cid.startswith("c") and cid[1:].isdigit():
                        all_ids.append(int(cid[1:]))
            next_num = max(all_ids, default=0) + 1
            candidate_id = f"c{next_num}"
            candidate_dict["id"] = candidate_id
            candidate_dict["votesCount"] = 0

            res = self.mongo_db.positions.update_one(
                {"_id": pos_id},
                {"$push": {"candidates": candidate_dict}}
            )
            if res.matched_count == 0:
                return False, "Position not found."
            return True, candidate_dict
        else:
            store = self._read_local_store()
            positions = store.get("positions", [])
            pos = next((p for p in positions if p["id"] == pos_id), None)
            if not pos:
                return False, "Position not found."

            all_ids = []
            for p in positions:
                for c in p.get("candidates", []):
                    cid = c.get("id", "")
                    if cid.startswith("c") and cid[1:].isdigit():
                        all_ids.append(int(cid[1:]))
            next_num = max(all_ids, default=0) + 1
            candidate_id = f"c{next_num}"
            candidate_dict["id"] = candidate_id
            candidate_dict["votesCount"] = 0

            pos.setdefault("candidates", []).append(candidate_dict)
            self._write_local_store(store)
            return True, candidate_dict

    def delete_candidate(self, candidate_id):
        cid = candidate_id.strip()
        if self.use_mongodb:
            res = self.mongo_db.positions.update_many(
                {},
                {"$pull": {"candidates": {"id": cid}}}
            )
            if res.modified_count == 0:
                return False, "Candidate not found."
            return True, "Candidate deleted successfully."
        else:
            store = self._read_local_store()
            found = False
            for p in store.get("positions", []):
                before_len = len(p.get("candidates", []))
                p["candidates"] = [c for c in p.get("candidates", []) if c.get("id") != cid]
                if len(p["candidates"]) < before_len:
                    found = True
            if found:
                self._write_local_store(store)
                return True, "Candidate deleted successfully."
            return False, "Candidate not found."

    # ==================== ELECTION INFO & CONTROLS ====================

    def get_election_info(self):
        if self.use_mongodb:
            doc = self.mongo_db.election_info.find_one({"_id": "current"})
            if doc:
                doc.pop("_id", None)
                return doc
            return DEFAULT_ELECTION_INFO
        else:
            store = self._read_local_store()
            return store.get("electionInfo", DEFAULT_ELECTION_INFO)

    def set_election_status(self, status):
        status = "Open" if status.lower() == "open" else "Closed"
        if self.use_mongodb:
            self.mongo_db.election_info.update_one(
                {"_id": "current"},
                {"$set": {"status": status}},
                upsert=True
            )
            return True, status
        else:
            store = self._read_local_store()
            store.setdefault("electionInfo", DEFAULT_ELECTION_INFO)["status"] = status
            self._write_local_store(store)
            return True, status

    # ==================== OTP SYSTEM ====================

    def store_otp(self, reg_no, expiry_minutes=5):
        reg_no = reg_no.strip().upper()
        # Generate clean 6-digit numeric OTP
        otp_code = "".join(secrets.choice("0123456789") for _ in range(6))
        expires_at = time.time() + (expiry_minutes * 60)

        otp_doc = {
            "regNo": reg_no,
            "otp": otp_code,
            "expiresAt": expires_at,
            "used": False
        }

        if self.use_mongodb:
            self.mongo_db.otps.update_one(
                {"regNo": reg_no},
                {"$set": otp_doc},
                upsert=True
            )
        else:
            store = self._read_local_store()
            store.setdefault("otps", {})[reg_no] = otp_doc
            self._write_local_store(store)

        return otp_code

    def verify_otp(self, reg_no, otp_code):
        reg_no = reg_no.strip().upper()
        otp_code = (otp_code or "").strip()

        if self.use_mongodb:
            doc = self.mongo_db.otps.find_one({"regNo": reg_no, "used": False})
            if not doc:
                return False, "No active OTP request found. Please request a new OTP."
            if time.time() > doc.get("expiresAt", 0):
                return False, "OTP has expired. Please request a new code."
            if doc.get("otp") != otp_code:
                return False, "Invalid OTP code. Please try again."

            # Mark OTP as used
            self.mongo_db.otps.update_one({"regNo": reg_no}, {"$set": {"used": True}})
            return True, "OTP verified successfully."
        else:
            store = self._read_local_store()
            doc = store.get("otps", {}).get(reg_no)
            if not doc or doc.get("used"):
                return False, "No active OTP request found. Please request a new OTP."
            if time.time() > doc.get("expiresAt", 0):
                return False, "OTP has expired. Please request a new code."
            if doc.get("otp") != otp_code:
                return False, "Invalid OTP code. Please try again."

            doc["used"] = True
            self._write_local_store(store)
            return True, "OTP verified successfully."

    # ==================== VOTING & LOCKING ====================

    def cast_vote(self, reg_no, ballot_selections):
        """
        Atomically records ballot submission, generates cryptographic receipt,
        and permanently locks the student's voting status to prevent duplicate votes.
        """
        reg_no = reg_no.strip().upper()
        student = self.get_student(reg_no)

        if not student:
            return False, "Student not found in voter roll."

        if not student.get("isEligible", False):
            return False, "Student is not eligible to vote in this election."

        if student.get("hasVoted", False):
            return False, "Ballot has already been submitted and locked for this student."

        election_info = self.get_election_info()
        if election_info.get("status") != "Open":
            return False, "Elections are currently closed."

        # Validate that all required positions have a selection
        positions = self.get_positions()
        for pos in positions:
            pos_id = pos["id"]
            if pos_id not in ballot_selections:
                return False, f"Missing selection for {pos['title']}."
            cand_id = ballot_selections[pos_id]
            valid_cands = [c["id"] for c in pos.get("candidates", [])]
            if cand_id not in valid_cands:
                return False, f"Invalid candidate selection for {pos['title']}."

        # Generate cryptographic receipt hash (SHA-256)
        timestamp_str = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
        raw_token = f"{reg_no}:{timestamp_str}:{secrets.token_hex(16)}"
        receipt_hash = "0x" + hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

        # Update Candidate Vote Counts & Lock Student Ballot
        if self.use_mongodb:
            # Increment candidate vote counts
            for pos_id, cand_id in ballot_selections.items():
                self.mongo_db.positions.update_one(
                    {"_id": pos_id, "candidates.id": cand_id},
                    {"$inc": {"candidates.$.votesCount": 1}}
                )

            # Lock Student Record
            self.mongo_db.students.update_one(
                {"_id": reg_no},
                {"$set": {
                    "hasVoted": True,
                    "votedAt": timestamp_str,
                    "receiptHash": receipt_hash,
                    "castedVotes": ballot_selections
                }}
            )
        else:
            store = self._read_local_store()

            # Increment candidate votes in local store
            for p in store.get("positions", []):
                pos_id = p["id"]
                if pos_id in ballot_selections:
                    sel_cand = ballot_selections[pos_id]
                    for c in p.get("candidates", []):
                        if c["id"] == sel_cand:
                            c["votesCount"] = c.get("votesCount", 0) + 1

            # Lock Student in local store
            if reg_no in store.get("students", {}):
                store["students"][reg_no]["hasVoted"] = True
                store["students"][reg_no]["votedAt"] = timestamp_str
                store["students"][reg_no]["receiptHash"] = receipt_hash
                store["students"][reg_no]["castedVotes"] = ballot_selections

            self._write_local_store(store)

        receipt_data = {
            "studentName": student.get("name"),
            "regNo": reg_no,
            "timestamp": timestamp_str,
            "receiptHash": receipt_hash
        }

        return True, receipt_data

    # ==================== RESULTS & OVERVIEW STATS ====================

    def get_overview_stats(self):
        students = self.list_students()
        total = len(students)
        eligible = sum(1 for s in students if s.get("isEligible"))
        voted = sum(1 for s in students if s.get("hasVoted"))
        remaining = eligible - sum(1 for s in students if s.get("isEligible") and s.get("hasVoted"))
        election_info = self.get_election_info()

        turnout_pct = round((voted / eligible * 100), 1) if eligible > 0 else 0.0

        return {
            "totalRegistered": total,
            "eligibleVoters": eligible,
            "votesCast": voted,
            "remainingVoters": max(0, remaining),
            "turnoutPercentage": turnout_pct,
            "electionStatus": election_info.get("status", "Open"),
            "databaseMode": "MongoDB Atlas" if self.use_mongodb else "Local Document Store"
        }

    def get_results(self):
        positions = self.get_positions()
        # Retrieve all eligible students who have cast ballots
        voted_students = self.list_students(eligibility="eligible", voting_status="voted")

        # Dynamically tally genuine ballots from castedVotes
        tallies = {}
        for pos in positions:
            pos_id = pos.get("id")
            tallies[pos_id] = {c.get("id"): 0 for c in pos.get("candidates", [])}

        for s in voted_students:
            casted = s.get("castedVotes") or {}
            for pos_id, cand_id in casted.items():
                if pos_id in tallies and cand_id in tallies[pos_id]:
                    tallies[pos_id][cand_id] += 1

        results = []
        for pos in positions:
            pos_id = pos.get("id")
            pos_tallies = tallies.get(pos_id, {})
            total_pos_votes = sum(pos_tallies.values())
            cand_results = []

            for cand in pos.get("candidates", []):
                cid = cand.get("id")
                vc = pos_tallies.get(cid, 0)
                pct = round((vc / total_pos_votes * 100), 1) if total_pos_votes > 0 else 0.0
                cand_results.append({
                    "id": cid,
                    "name": cand.get("name"),
                    "major": cand.get("major"),
                    "year": cand.get("year"),
                    "votesCount": vc,
                    "percentage": pct
                })

            results.append({
                "positionId": pos_id,
                "positionTitle": pos.get("title"),
                "totalVotes": total_pos_votes,
                "candidates": cand_results
            })

        return results


# Global Singleton Instance
db = DatabaseManager()
