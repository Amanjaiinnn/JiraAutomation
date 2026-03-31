const express = require("express");
const cors = require("cors");

const app = express();
const state = {
  auth: []
};

app.use(cors({ origin: ["http://localhost:5173", "http://localhost:5174"] }));
app.use(express.json());

app.get("/auth/sessions", (_req, res) => res.json(state.auth));
app.post("/auth/login", (req, res) => {
  const item = { id: state.auth.length + 1, workflow: "login", ...req.body };
  state.auth.push(item);
  res.json({ message: "As a user, I want to register with a valid email and password to access the system. completed", data: item });
});
app.post("/auth/login-2", (req, res) => {
  const item = { id: state.auth.length + 1, workflow: "login-2", ...req.body };
  state.auth.push(item);
  res.json({ message: "As a user, I want to log in with a valid email and password to access the system. completed", data: item });
});

app.get("/health", (_req, res) => res.json({ status: "ok" }));

app.listen(8001, () => {
  console.log("Generated backend running on http://localhost:8001");
});
