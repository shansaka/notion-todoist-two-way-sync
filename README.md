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

Configure your Notion and Todoist API keys and other settings using environment variables. See the code for required variables.

## Files

- `app.py`: Main application logic for syncing tasks.
- `requirements.txt`: Python dependencies.
- `Dockerfile`: Docker configuration for containerized deployment.

## License

MIT

## Author

shansaka
