# Notion-Todoist Two-Way Sync

This project provides a two-way synchronization between Notion and Todoist, allowing tasks to be kept in sync across both platforms.

## Features

- Sync tasks between Notion and Todoist
- Docker support for easy deployment
- Simple configuration via environment variables

## Getting Started

### Prerequisites

- Python 3.8+
- Docker (optional)

### Installation

1. Clone the repository:
   ```powershell
   git clone https://github.com/shansaka/notion-todoist-two-way-sync.git
   cd notion-todoist-two-way-sync
   ```
2. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```

### Usage

Run the application:

```powershell
python app.py
```

### Docker

To run with Docker:

1. Build the image:
   ```powershell
   docker build -t notion-todoist-sync .
   ```
2. Run the container:
   ```powershell
   docker run --env-file .env notion-todoist-sync
   ```

## Configuration

Configure your Notion and Todoist API keys and other settings using environment variables. Below are the required environment variables:

### Required Environment Variables

#### Notion

- `NOTION_TOKEN`: Your Notion integration token
- `NOTION_DATABASE_ID`: The ID of your Notion database

#### Todoist

- `TODOIST_API_KEY`: Your Todoist API key

#### Email Notifications (optional, for error alerts)

- `EMAIL_HOST`: SMTP server host
- `EMAIL_PORT`: SMTP server port (default: 587)
- `EMAIL_USER`: Email address to send from
- `EMAIL_PASS`: Email password or app password
- `EMAIL_TO`: Recipient email address (defaults to `EMAIL_USER` if not set)

Set these variables in your environment or in a `.env` file for Docker usage.

## Files

- `app.py`: Main application logic for syncing tasks.
- `requirements.txt`: Python dependencies.
- `Dockerfile`: Docker configuration for containerized deployment.

## License

MIT

## Author

shansaka
