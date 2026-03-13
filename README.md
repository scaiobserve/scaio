# Legislative Watchdog Engine

The Legislative Watchdog Engine is a Python-based automation pipeline designed for the South Carolina AI Observatory (SCAIO). It tracks, analyzes, and drafts content about AI-related legislation in South Carolina and the US Congress.

## Features

1.  **Data Ingestion:** Connects to the LegiScan API to search for recently introduced or updated legislation matching specific AI-related keywords in South Carolina (SC) and the US Congress.
2.  **LLM Analysis:** Uses OpenAI to analyze the bills, providing a 3-bullet executive summary, a "South Carolina Business Impact Score" (1-10), and a short explanation of the impact on local governments, manufacturers, or the regional tech economy.
3.  **Output Generation:** Generates clean Markdown files with YAML frontmatter for ingestion into a CMS or static site generator.

## Setup Instructions

### Prerequisites
- Python 3.9+

### 1. Clone the repository and install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy the example environment file and fill in your API keys:

```bash
cp .env.example .env
```

You will need:
- A LegiScan API Key: [Register here](https://legiscan.com/legiscan)
- An OpenAI API Key: [Get it here](https://platform.openai.com)

### 3. Run Locally

Execute the main script to run the job locally:

```bash
python main.py
```

The script will query the APIs and output the results as markdown files in the `drafts/` directory.

## Cron Job Setup (Render / Railway)

To run this as a daily cron job on platforms like Render or Railway:

1.  **Environment Variables:** Add `LEGISCAN_API_KEY` and `OPENAI_API_KEY` directly in your project's settings dashboard on the platform.
2.  **Continuous Integration:** Connect your GitHub repository to the platform.
3.  **Cron Schedule:** Set up a Cron Job service. Define the schedule using a standard cron expression. E.g., `0 8 * * *` will run it every day at 8:00 AM UTC.
4.  **Runtime Command:** Specify the start command as `python main.py`.

*Note: Since the output is generated locally in the `drafts/` directory, depending on how your CMS ingests this info, you might need to add a step to the pipeline to push the generated markdown files to another repository, a database, or an API endpoints.*
