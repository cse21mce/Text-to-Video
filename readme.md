# Setup

## Clone the Repository

```bash
git clone https://github.com/cse21mce/Text-to-Video.git
```

## Create Enviornment

` Install Python version 3.10 for compatibility.`

```bash
python --version
# Python 3.10.0

python -m venv venv
.\venv\Scripts\activate
```

## Dependencies Installatoin

```bash
pip install -r ./requirments.txt

git clone https://github.com/VarunGumma/IndicTransToolkit
cd IndicTransToolkit
pip install --editable ./
```

## Setup Enviournment Variables

```bash
MONGO_URI="mongodb://localhost:27017/pib"
OPENAI_API_KEY="OPENAI_API_KEY"
GOOGLE_API_KEY="GOOGLE_API_KEY"
SEARCH_ENGINE_ID="SEARCH_ENGINE_ID"
```

## Run the API

```bash
pyhton app.py
```

# Usage

## Endpoint

`Input`

```json
query={
    url="https://pib.gov.in/PressReleasePage.aspx?PRID=2096307"
}

example = "http://0.0.0.0:8000/text-to-video?url=https://pib.gov.in/PressReleasePage.aspx?PRID=2096307"

```

`Output`

```json

```
