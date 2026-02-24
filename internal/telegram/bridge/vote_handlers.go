package bridge

import (
	"encoding/json"
	"net/http"

	"github.com/vlle/Photoshnaya/internal/domain/voteflow"
)

const (
	startVotePath  = "/internal/v1/vote/start"
	nextVotePath   = "/internal/v1/vote/next"
	prevVotePath   = "/internal/v1/vote/prev"
	likeVotePath   = "/internal/v1/vote/like"
	unlikeVotePath = "/internal/v1/vote/unlike"
	submitVotePath = "/internal/v1/vote/submit"
)

type startVoteRequest struct {
	Text     string `json:"text"`
	ChatType string `json:"chat_type"`
	UserID   int64  `json:"user_id"`
	UserName string `json:"user_name"`
	FullName string `json:"user_full_name"`
}

type navigateVoteRequest struct {
	UserID            int64 `json:"user_id"`
	GroupID           int64 `json:"group_id"`
	CurrentPhotoID    int64 `json:"current_photo_id"`
	CurrentPhotoCount int   `json:"current_photo_count"`
	AmountPhotos      int   `json:"amount_photos"`
}

type submitVoteRequest struct {
	UserID  int64 `json:"user_id"`
	GroupID int64 `json:"group_id"`
}

func (h *Handler) registerVoteRoutes(mux *http.ServeMux) {
	if h.vote == nil {
		return
	}
	mux.HandleFunc(startVotePath, h.startVote)
	mux.HandleFunc(nextVotePath, h.nextVote)
	mux.HandleFunc(prevVotePath, h.prevVote)
	mux.HandleFunc(likeVotePath, h.likeVote)
	mux.HandleFunc(unlikeVotePath, h.unlikeVote)
	mux.HandleFunc(submitVotePath, h.submitVote)
}

func (h *Handler) startVote(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeError(w, http.StatusMethodNotAllowed, "method_not_allowed")
		return
	}

	var req startVoteRequest
	if !decodeJSON(w, r, &req) {
		return
	}

	result := h.vote.StartVoteSession(r.Context(), voteflow.StartRequest{
		Text:     req.Text,
		ChatType: req.ChatType,
		UserID:   req.UserID,
		UserName: req.UserName,
		FullName: req.FullName,
	})
	writeJSON(w, http.StatusOK, result)
}

func (h *Handler) nextVote(w http.ResponseWriter, r *http.Request) {
	h.navigate(w, r, "next")
}

func (h *Handler) prevVote(w http.ResponseWriter, r *http.Request) {
	h.navigate(w, r, "prev")
}

func (h *Handler) navigate(w http.ResponseWriter, r *http.Request, direction string) {
	if r.Method != http.MethodPost {
		writeError(w, http.StatusMethodNotAllowed, "method_not_allowed")
		return
	}

	var req navigateVoteRequest
	if !decodeJSON(w, r, &req) {
		return
	}

	result := h.vote.Navigate(r.Context(), voteflow.NavigateRequest{
		Direction:         direction,
		UserID:            req.UserID,
		GroupID:           req.GroupID,
		CurrentPhotoID:    req.CurrentPhotoID,
		CurrentPhotoCount: req.CurrentPhotoCount,
		AmountPhotos:      req.AmountPhotos,
	})
	writeJSON(w, http.StatusOK, result)
}

func (h *Handler) likeVote(w http.ResponseWriter, r *http.Request) {
	h.likeAction(w, r, true)
}

func (h *Handler) unlikeVote(w http.ResponseWriter, r *http.Request) {
	h.likeAction(w, r, false)
}

func (h *Handler) likeAction(w http.ResponseWriter, r *http.Request, setLike bool) {
	if r.Method != http.MethodPost {
		writeError(w, http.StatusMethodNotAllowed, "method_not_allowed")
		return
	}

	var req navigateVoteRequest
	if !decodeJSON(w, r, &req) {
		return
	}

	likeReq := voteflow.LikeRequest{
		UserID:            req.UserID,
		GroupID:           req.GroupID,
		CurrentPhotoID:    req.CurrentPhotoID,
		CurrentPhotoCount: req.CurrentPhotoCount,
		AmountPhotos:      req.AmountPhotos,
	}

	var result voteflow.ActionResult
	if setLike {
		result = h.vote.SetLike(r.Context(), likeReq)
	} else {
		result = h.vote.UnsetLike(r.Context(), likeReq)
	}
	writeJSON(w, http.StatusOK, result)
}

func (h *Handler) submitVote(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeError(w, http.StatusMethodNotAllowed, "method_not_allowed")
		return
	}

	var req submitVoteRequest
	if !decodeJSON(w, r, &req) {
		return
	}

	result := h.vote.SubmitVote(r.Context(), voteflow.SubmitRequest{
		UserID:  req.UserID,
		GroupID: req.GroupID,
	})
	writeJSON(w, http.StatusOK, result)
}

func decodeJSON(w http.ResponseWriter, r *http.Request, dst any) bool {
	decoder := json.NewDecoder(r.Body)
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(dst); err != nil {
		writeError(w, http.StatusBadRequest, "invalid_payload")
		return false
	}
	return true
}
