(() => {
  "use strict";

  const API_PREFIX = "/api";
  const encode = (value) => encodeURIComponent(String(value));

  function createApiError(response, payload) {
    const detail = payload && typeof payload.detail === "string" ? payload.detail : null;
    const message = payload && typeof payload.message === "string"
      ? payload.message
      : detail || `Yêu cầu thất bại (${response.status}).`;
    const error = new Error(message);
    error.status = response.status;
    error.code = payload && payload.error_code ? payload.error_code : "HTTP_ERROR";
    error.retryable = Boolean(payload && payload.retryable);
    error.recoveryAction = payload && typeof payload.recovery_action === "string"
      ? payload.recovery_action
      : null;
    error.payload = payload;
    return error;
  }

  async function request(path, { method = "GET", body } = {}) {
    const headers = { accept: "application/json" };
    const options = {
      method,
      credentials: "same-origin",
      headers,
    };
    if (body !== undefined) {
      headers["content-type"] = "application/json";
      options.body = JSON.stringify(body);
    }

    let response;
    try {
      response = await fetch(`${API_PREFIX}${path}`, options);
    } catch (_cause) {
      const error = new Error("Không thể kết nối tới máy chủ. Hãy kiểm tra mạng rồi thử lại.");
      error.status = null;
      error.code = "NETWORK_ERROR";
      error.retryable = true;
      error.recoveryAction = "Nội dung đã lưu trên máy chủ vẫn được giữ nguyên.";
      throw error;
    }

    if (response.status === 204) return null;
    const payload = await response.json().catch(() => null);
    if (!response.ok) throw createApiError(response, payload);
    if (payload === null) {
      const error = new Error("Máy chủ trả về dữ liệu không đọc được.");
      error.status = response.status;
      error.code = "INVALID_RESPONSE";
      error.retryable = false;
      error.recoveryAction = null;
      throw error;
    }
    return payload;
  }

  const api = {
    createSession(payload) {
      return request("/sessions", { method: "POST", body: payload });
    },
    getSession(sessionId) {
      return request(`/sessions/${encode(sessionId)}`);
    },
    submitAnswer(sessionId, payload) {
      return request(`/sessions/${encode(sessionId)}/answers`, { method: "POST", body: payload });
    },
    evaluateAnswer(sessionId, answerId, answerRevision) {
      return request(`/sessions/${encode(sessionId)}/answers/${encode(answerId)}/evaluate`, {
        method: "POST",
        body: { answer_revision: answerRevision },
      });
    },
    getEvaluation(sessionId, answerId, answerRevision) {
      return request(`/sessions/${encode(sessionId)}/answers/${encode(answerId)}/evaluations/${encode(answerRevision)}`);
    },
    nextQuestion(sessionId, fromQuestionIndex) {
      return request(`/sessions/${encode(sessionId)}/next`, {
        method: "POST",
        body: { from_question_index: fromQuestionIndex },
      });
    },
    endSession(sessionId, reason = "student_requested") {
      return request(`/sessions/${encode(sessionId)}/end`, {
        method: "POST",
        body: { reason },
      });
    },
    getSessionSummary(sessionId) {
      return request(`/sessions/${encode(sessionId)}/summary`);
    },
    getExerciseRecommendations(sessionId) {
      return request(`/sessions/${encode(sessionId)}/exercises`);
    },
    getExercise(exerciseId, version) {
      const query = version == null ? "" : `?version=${encode(version)}`;
      return request(`/exercises/${encode(exerciseId)}${query}`);
    },
    startPractice(sessionId, answerId, payload) {
      return request(`/sessions/${encode(sessionId)}/answers/${encode(answerId)}/practice`, {
        method: "POST",
        body: payload,
      });
    },
  };

  window.InterviewApi = Object.freeze(api);
})();
