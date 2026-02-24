package bridge

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"strconv"

	"github.com/vlle/Photoshnaya/internal/domain/leaderboard"
	"github.com/vlle/Photoshnaya/internal/domain/voteflow"
)

const winnersPath = "/internal/v1/leaderboards/winners"

type winnerService interface {
	WinnerRows(ctx context.Context, groupTelegramID int64, limit int32) ([]leaderboard.WinnerRow, error)
}

type voteService interface {
	StartVoteSession(ctx context.Context, req voteflow.StartRequest) voteflow.ActionResult
	Navigate(ctx context.Context, req voteflow.NavigateRequest) voteflow.ActionResult
	SetLike(ctx context.Context, req voteflow.LikeRequest) voteflow.ActionResult
	UnsetLike(ctx context.Context, req voteflow.LikeRequest) voteflow.ActionResult
	SubmitVote(ctx context.Context, req voteflow.SubmitRequest) voteflow.ActionResult
}

type Handler struct {
	winners winnerService
	vote    voteService
}

type leaderboardResponse struct {
	Text                  string `json:"text"`
	ParseMode             string `json:"parse_mode"`
	DisableWebPagePreview bool   `json:"disable_web_page_preview"`
}

func NewHandler(winners winnerService, vote voteService) *Handler {
	return &Handler{winners: winners, vote: vote}
}

func (h *Handler) RegisterRoutes(mux *http.ServeMux) {
	mux.HandleFunc("/healthz", h.healthz)
	mux.HandleFunc(winnersPath, h.winnersLeaderboard)
	h.registerVoteRoutes(mux)
}

func (h *Handler) healthz(w http.ResponseWriter, _ *http.Request) {
	w.WriteHeader(http.StatusOK)
	_, _ = w.Write([]byte("ok"))
}

func (h *Handler) winnersLeaderboard(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeError(w, http.StatusMethodNotAllowed, "method_not_allowed")
		return
	}

	groupIDRaw := r.URL.Query().Get("group_telegram_id")
	groupID, err := strconv.ParseInt(groupIDRaw, 10, 64)
	if err != nil || groupID == 0 {
		writeError(w, http.StatusBadRequest, "invalid_group_telegram_id")
		return
	}

	rows, err := h.winners.WinnerRows(r.Context(), groupID, leaderboard.TopLimit)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "query_failed")
		return
	}

	payload := leaderboardResponse{
		Text:                  leaderboard.FormatWinnerBoard(rows),
		ParseMode:             "HTML",
		DisableWebPagePreview: true,
	}
	writeJSON(w, http.StatusOK, payload)
}

func writeError(w http.ResponseWriter, status int, code string) {
	writeJSON(w, status, map[string]string{"error": code})
}

func writeJSON(w http.ResponseWriter, status int, payload any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	if err := json.NewEncoder(w).Encode(payload); err != nil && !errors.Is(err, context.Canceled) {
		http.Error(w, `{"error":"encode_failed"}`, http.StatusInternalServerError)
	}
}
