/**
 * College Digital Voting System - Client REST API Service
 */

const API = {
  baseUrl: '',

  async request(endpoint, options = {}) {
    const defaultHeaders = {
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    };

    const config = {
      ...options,
      headers: {
        ...defaultHeaders,
        ...options.headers
      }
    };

    try {
      const response = await fetch(`${this.baseUrl}${endpoint}`, config);
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.message || `Request failed with status ${response.status}`);
      }
      return data;
    } catch (err) {
      console.error(`[API Error] ${endpoint}:`, err);
      throw err;
    }
  },

  // Student Endpoints
  student: {
    async requestOtp(regNo) {
      return API.request('/api/student/request-otp', {
        method: 'POST',
        body: JSON.stringify({ regNo })
      });
    },

    async verifyOtp(regNo, otp) {
      return API.request('/api/student/verify-otp', {
        method: 'POST',
        body: JSON.stringify({ regNo, otp })
      });
    },

    async getMe(regNo) {
      return API.request(`/api/student/me?regNo=${encodeURIComponent(regNo)}`, {
        method: 'GET'
      });
    },

    async castVote(regNo, ballot) {
      return API.request('/api/student/vote', {
        method: 'POST',
        body: JSON.stringify({ regNo, ballot })
      });
    }
  },

  // Admin Endpoints
  admin: {
    async login(username, password) {
      return API.request('/api/admin/login', {
        method: 'POST',
        body: JSON.stringify({ username, password })
      });
    },

    async getOverview() {
      return API.request('/api/admin/overview', {
        method: 'GET'
      });
    },

    async getStudents(q = '', eligibility = 'all', votingStatus = 'all') {
      const params = new URLSearchParams({ q, eligibility, votingStatus });
      return API.request(`/api/admin/students?${params.toString()}`, {
        method: 'GET'
      });
    },

    async addStudent(studentData) {
      return API.request('/api/admin/students', {
        method: 'POST',
        body: JSON.stringify(studentData)
      });
    },

    async updateStudent(regNo, updateData) {
      return API.request(`/api/admin/students/${encodeURIComponent(regNo)}`, {
        method: 'PUT',
        body: JSON.stringify(updateData)
      });
    },

    async deleteStudent(regNo) {
      return API.request(`/api/admin/students/${encodeURIComponent(regNo)}`, {
        method: 'DELETE'
      });
    },

    async getCandidates() {
      return API.request('/api/admin/candidates', {
        method: 'GET'
      });
    },

    async addCandidate(candidateData) {
      return API.request('/api/admin/candidates', {
        method: 'POST',
        body: JSON.stringify(candidateData)
      });
    },

    async deleteCandidate(candidateId) {
      return API.request(`/api/admin/candidates/${encodeURIComponent(candidateId)}`, {
        method: 'DELETE'
      });
    },

    async getElectionInfo() {
      return API.request('/api/admin/election', {
        method: 'GET'
      });
    },

    async setElectionStatus(status) {
      return API.request('/api/admin/election/status', {
        method: 'POST',
        body: JSON.stringify({ status })
      });
    },

    async getResults() {
      return API.request('/api/admin/results', {
        method: 'GET'
      });
    }
  }
};

if (typeof window !== 'undefined') {
  window.API = API;
}
