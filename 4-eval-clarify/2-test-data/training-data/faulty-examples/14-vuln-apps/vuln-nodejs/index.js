// Intentionally vulnerable Node.js app for JSA testing
// Contains various security issues for scanners to catch

const express = require('express');
const { exec } = require('child_process');
const config = require('./config');

const app = express();

// VULN: No input sanitization - command injection
app.get('/run', (req, res) => {
  const cmd = req.query.cmd;
  exec(cmd, (error, stdout, stderr) => {  // VULN: command injection
    res.send(stdout || stderr);
  });
});

// VULN: SQL injection (simulated)
app.get('/user', (req, res) => {
  const id = req.query.id;
  const query = `SELECT * FROM users WHERE id = ${id}`;  // VULN: SQL injection
  // Simulated DB query
  res.send({ query: query });
});

// VULN: XSS - reflecting user input without sanitization
app.get('/greet', (req, res) => {
  const name = req.query.name;
  res.send(`<h1>Hello ${name}!</h1>`);  // VULN: XSS
});

// VULN: Sensitive data exposure
app.get('/config', (req, res) => {
  res.json(config);  // VULN: exposing secrets
});

// VULN: Insecure random
app.get('/token', (req, res) => {
  const token = Math.random().toString(36);  // VULN: weak randomness
  res.json({ token });
});

// VULN: Hardcoded credentials in code
const ADMIN_PASSWORD = "admin123";  // VULN: hardcoded password

app.listen(3000, () => {
  console.log('Vulnerable app running on port 3000');
});
