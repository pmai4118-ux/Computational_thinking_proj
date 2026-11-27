(() => {
  "use strict";

  const API_PREFIX = "/api";
  const encode = (value) => encodeURIComponent(String(value));

  function createApiError(response, payload) {
    let message = payload && typeof payload.message === "string" ? payload.message : null;
    const fieldErrors = payload && typeof payload.field_errors === "object" && payload.field_errors !== null
      ? { ...payload.field_errors }
      : {};

    if (!message) {
      if (payload && typeof payload.detail === "string") {
        message = payload.detail;
      } else if (payload && Array.isArray(payload.detail)) {
        const details = [];
        for (const item of payload.detail) {
          const key = Array.isArray(item.loc) ? item.loc.filter((p) => p !== "body").join(".") : "";
          const msg = item.msg || "Giá trị không hợp lệ.";
          if (key) {
            fieldErrors[key] = msg;
            details.push(`${key}: ${msg}`);
          } else {
            details.push(msg);
          }
        }
        message = details.length ? `Dữ liệu không hợp lệ: ${details.join("; ")}` : `Dữ liệu không hợp lệ (${response.status}).`;
      } else if (response.status === 410) {
        message = "Phiên luyện tập đã hết hạn khả dụng.";
      } else if (response.status === 403) {
        message = "Bạn không có quyền truy cập phiên này.";
      } else if (response.status === 404) {
        message = "Không tìm thấy tài nguyên yêu cầu.";
      } else {
        message = `Yêu cầu thất bại (${response.status}).`;
      }
    }

    let code = payload && payload.error_code ? payload.error_code : "HTTP_ERROR";
    if (code === "HTTP_ERROR") {
      if (response.status === 410) code = "SESSION_EXPIRED";
      else if (response.status === 403) code = "SESSION_FORBIDDEN";
      else if (response.status === 404) code = "NOT_FOUND";
      else if (response.status === 409) code = "CONFLICT";
      else if (response.status === 422) code = "INVALID_INPUT";
      else if (response.status === 504) code = "PROVIDER_TIMEOUT";
    }

    const retryable = payload && typeof payload.retryable === "boolean"
      ? payload.retryable
      : (response.status === 502 || response.status === 503 || response.status === 504 || response.status === 429);

    let recoveryAction = payload && typeof payload.recovery_action === "string"
      ? payload.recovery_action
      : null;
    if (!recoveryAction) {
      if (code === "SESSION_EXPIRED") {
        recoveryAction = "Bắt đầu phiên luyện tập mới.";
      } else if (code === "SESSION_FORBIDDEN") {
        recoveryAction = "Mở phiên của bạn hoặc bắt đầu phiên mới.";
      } else if (code === "PROVIDER_TIMEOUT" || retryable) {
        recoveryAction = "Bài trả lời đã lưu trên máy chủ; bạn có thể thử đánh giá lại.";
      }
    }

    const error = new Error(message);
    error.status = response.status;
    error.code = code;
    error.retryable = retryable;
    error.recoveryAction = recoveryAction;
    error.fieldErrors = fieldErrors;
    error.clientSubmissionId = payload && typeof payload.client_submission_id === "string" ? payload.client_submission_id : null;
    error.sessionId = payload && typeof payload.session_id === "string" ? payload.session_id : null;
    error.answerRef = payload && typeof payload.answer_ref === "object" ? payload.answer_ref : null;
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
      return request("/sessions", {
        method: "POST", body: { evaluation_timing: "after_session", ...payload },
      });
    },
    getSession(sessionId) {
      return request(`/sessions/${encode(sessionId)}`);
    },
    submitAnswer(sessionId, payload) {
      return request(`/sessions/${encode(sessionId)}/answers`, { method: "POST", body: payload });
    },
    saveDraft(sessionId, payload) {
      return request(`/sessions/${encode(sessionId)}/draft`, { method: "PUT", body: payload });
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
    getFollowUpPlan(sessionId, answerId, answerRevision) {
      const query = answerRevision == null ? "" : `?revision=${encode(answerRevision)}`;
      return request(`/sessions/${encode(sessionId)}/answers/${encode(answerId)}/follow-up${query}`);
    },
    submitFollowUp(sessionId, answerId, payload) {
      return request(`/sessions/${encode(sessionId)}/answers/${encode(answerId)}/follow-up`, {
        method: "POST",
        body: payload,
      });
    },
    getAnswerReplay(sessionId, answerId, answerRevision) {
      const query = answerRevision == null ? "" : `?revision=${encode(answerRevision)}`;
      return request(`/sessions/${encode(sessionId)}/answers/${encode(answerId)}/replay${query}`);
    },
  };

  window.InterviewApi = Object.freeze(api);
})();
