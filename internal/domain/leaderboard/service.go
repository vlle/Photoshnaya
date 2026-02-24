package leaderboard

import (
	"context"
	"fmt"
	"html"
	"net/url"
	"strings"
)

const (
	EmptyLeaderboardMessage = "Пока нет данных."
	TopLimit                = int32(20)
)

type WinnerRow struct {
	Name  string
	Total int64
}

type Repository interface {
	TopWinners(ctx context.Context, groupTelegramID int64, limit int32) ([]WinnerRow, error)
}

type Service struct {
	repo Repository
}

func NewService(repo Repository) *Service {
	return &Service{repo: repo}
}

func (s *Service) WinnerRows(ctx context.Context, groupTelegramID int64, limit int32) ([]WinnerRow, error) {
	return s.repo.TopWinners(ctx, groupTelegramID, limit)
}

func FormatWinnerBoard(rows []WinnerRow) string {
	if len(rows) == 0 {
		return EmptyLeaderboardMessage
	}

	var sb strings.Builder
	for i, row := range rows {
		escapedName := html.EscapeString(row.Name)
		link := fmt.Sprintf(
			"<a href=\"https://t.me/%s\">%s</a>",
			url.PathEscape(row.Name),
			escapedName,
		)
		fmt.Fprintf(&sb, "<b>%d</b>: %s, количество побед: %d\n", i+1, link, row.Total)
	}

	return sb.String()
}
