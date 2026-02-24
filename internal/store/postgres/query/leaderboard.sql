-- name: SelectWinnerLeaderboard :many
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
