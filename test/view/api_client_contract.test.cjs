"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const apiClientScript = fs.readFileSync(
  path.join(__dirname, "../../source/view/static/js/api_client.js"),
  "utf8"
);

function loadApiClient(fetchImpl) {
  const window = {};
  vm.runInNewContext(apiClientScript, {
    window,
    fetch: fetchImpl || (async () => ({ status: 200, ok: true, json: async () => ({}) })),
    Error,
    encodeURIComponent,
    JSON,
    String,
    Array,
  });
  return window.InterviewApi;
}

test("api_client exposes draft, submit, follow-up, and replay methods", async () => {
  const calls = [];
  const api = loadApiClient(async (url, options) => {
    calls.push({ url, options });
    return { status: 200, ok: true, json: async () => ({ ok: true }) };
  });

  for (const method of [
    "createSession",
    "getSession",
    "submitAnswer",
    "saveDraft",
    "evaluateAnswer",
    "getEvaluation",
    "nextQuestion",
    "endSession",
    "getSessionSummary",
    "getExerciseRecommendations",
    "getExercise",
    "getFollowUpPlan",
    "submitFollowUp",
    "getAnswerReplay",
    "getReplayHub",
    "getReplayRun",
    "selectReplayNode",
    "chooseReplayOption",
    "rewindReplayNode",
    "addCustomReplayBranch",
  ]) {
    assert.equal(typeof api[method], "function", `missing InterviewApi.${method}`);
  }

  await api.saveDraft("session-1", { question_id: "q-1", question_version: 1, text: "hello" });
  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, "/api/sessions/session-1/draft");
  assert.equal(calls[0].options.method, "PUT");
  assert.equal(calls[0].options.credentials, "same-origin");
  assert.deepEqual(JSON.parse(calls[0].options.body), {
    question_id: "q-1",
    question_version: 1,
    text: "hello",
  });
});
