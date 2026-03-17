# Photoshnaya

[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)


Telegram-based application for photo-contests in group chats. Allows for instant photo registration and tracks contest themes with #. Also includes an admin menu for easy management and a leaderboard for tracking results.

To access the bot, use the [@photoshnaya_bot](t.me/photoshnaya_bot) handle or go to [How to Use](#how-to-use) section for self-host.


## Features

-  Instant photo registration through contest themes followed by #
-  Restricts user's photo registration to one per contest
-  Includes an easy-to-use admin menu at /admin
-  Uploads the winner's photo as the group chat photo
-  Tracks results and generates a leaderboard for both winners and participants

## How to Use:

   1) Clone the repository and rename env.example to .env.
   2) Fill in the bot token and postgre_url in the .env file.
   3) Start the application by using docker-compose up --build -d.

## CI Deploy

GitHub Actions can build, push, and deploy the bot to a remote host over SSH after tests pass on `main`.

Required GitHub secrets:

- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN`
- `DEPLOY_HOST`
- `DEPLOY_USER`
- `DEPLOY_SSH_KEY`
- `DEPLOY_KNOWN_HOSTS`
- `DEPLOY_PATH`
- `DEPLOY_PORT` (optional, defaults to `22`)

Remote host requirements:

- Docker with `docker compose` or `docker-compose`
- checked-out project directory at `DEPLOY_PATH`
- production env already present on the server

Deployment flow:

1. CI runs flake8 and `docker compose -f docker-compose.test.yml up`.
2. On push to `main`, CI builds and pushes `${DOCKERHUB_USERNAME}/photoshnaya_bot` with `latest` and `${GITHUB_SHA}` tags.
3. CI SSHes to the remote host, exports `IMAGE_REPOSITORY` and `IMAGE_TAG`, then runs `docker compose pull web && docker compose up -d web`.
   4) Switch off Group Privacy for the bot via BotFather menu.
   5) Add bot to the needed group and grant administration rights.
   6) Shutdown the application with docker-compose down.

## System Requirements:

- This application should work on any platform that supports Docker.

## Screenshots:

![Admin menu](screenshots/admin_menu1.png "Admin menu")
![Voting menu](screenshots/vote.png "Voting menu")
![Contest registration via # tracking](screenshots/photo_accepted.png "Confirmation message")
