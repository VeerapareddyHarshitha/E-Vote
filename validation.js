/**
 * College Digital Voting System - Form & Security Validation
 */

const ValidationModule = {
  // Regex pattern for Student Registration Number
  // Must contain exactly 9 characters, start with 11, remaining 7 characters uppercase letters (A-Z) and digits (0-9).
  regNoPattern: /^11[A-Z0-9]{7}$/,
  otpPattern: /^[0-9]{6}$/,

  /**
   * Validate Registration Number format and mandatory presence
   */
  validateRegistrationNumber(value) {
    const trimmed = (value || '').trim().toUpperCase();
    if (!trimmed || !this.regNoPattern.test(trimmed)) {
      return {
        isValid: false,
        message: "Enter a valid 9-character registration number starting with 11."
      };
    }

    return {
      isValid: true,
      message: "Valid registration number format."
    };
  },

  /**
   * Validate 6-digit OTP format
   */
  validateOtp(value) {
    const trimmed = (value || '').trim();
    if (!trimmed || !this.otpPattern.test(trimmed)) {
      return {
        isValid: false,
        message: "Enter the 6-digit verification code sent to your college email."
      };
    }

    return {
      isValid: true,
      message: "Valid OTP format."
    };
  },

  /**
   * Derive Institutional College Email from Registration Number
   * [REGISTER_NUMBER]@kanchiuniv.ac.in
   */
  deriveCollegeEmail(regNo) {
    const trimmed = (regNo || '').trim().toUpperCase();
    if (this.regNoPattern.test(trimmed)) {
      return `${trimmed}@kanchiuniv.ac.in`;
    }
    return '';
  },

  /**
   * Check if registration number input is filled and valid
   */
  isFormFilled(regNoValue) {
    const trimmed = (regNoValue || '').trim().toUpperCase();
    return this.regNoPattern.test(trimmed);
  }
};

if (typeof window !== 'undefined') {
  window.ValidationModule = ValidationModule;
}
