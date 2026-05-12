// Intentionally vulnerable config for JSA testing
// DO NOT USE IN PRODUCTION

module.exports = {
  // Hardcoded secrets (gitleaks should catch)
  database: {
    host: "localhost",
    user: "admin",
    password: "SuperSecret123!",  // VULN: hardcoded password
    api_key: "sk-proj-1234567890abcdefghijklmnop"  // VULN: hardcoded API key
  },

  // AWS credentials (gitleaks should catch)
  aws: {
    accessKeyId: "AKIAIOSFODNN7EXAMPLE",  // VULN: hardcoded AWS key
    secretAccessKey: "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"  // VULN: hardcoded secret
  },

  jwt: {
    secret: "my-super-secret-jwt-key-12345"  // VULN: hardcoded JWT secret
  }
};
