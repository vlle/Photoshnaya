package repo

import (
	"context"

	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/vlle/Photoshnaya/internal/domain/leaderboard"
)

const topWinnersSQL = `
SELECT
    u.name,
    COUNT(cw.contest_id) AS total
FROM contest_winner cw
JOIN contest c ON cw.contest_id = c.id
JOIN "user" u ON cw.user_id = u.id
JOIN "group" g ON c.group_id = g.id
WHERE g.telegram_id = $1
GROUP BY u.id
ORDER BY COUNT(cw.contest_id) DESC
LIMIT $2;
`

type LeaderboardRepo struct {
	pool *pgxpool.Pool
}

func NewLeaderboardRepo(pool *pgxpool.Pool) *LeaderboardRepo {
	return &LeaderboardRepo{pool: pool}
}

func (r *LeaderboardRepo) TopWinners(ctx context.Context, groupTelegramID int64, limit int32) ([]leaderboard.WinnerRow, error) {
	rows, err := r.pool.Query(ctx, topWinnersSQL, groupTelegramID, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	winners := make([]leaderboard.WinnerRow, 0)
	for rows.Next() {
		var row leaderboard.WinnerRow
		if err := rows.Scan(&row.Name, &row.Total); err != nil {
			return nil, err
		}
		winners = append(winners, row)
	}

	if err := rows.Err(); err != nil {
		return nil, err
	}

	return winners, nil
}
