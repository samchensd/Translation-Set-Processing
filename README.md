# Translation Set Processing

This project processes multiple Excel files containing translations and combines them into a single consolidated output file.

## Project Structure
```
.
├── README.md
├── requirements.txt
├── src/
│   ├── __init__.py
│   ├── excel_processor.py
│   ├── utils.py
│   └── config.py
├── data/
│   ├── input/
│   └── output/
└── logs/
```

## Setup and Installation

1. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Place your input Excel files in the `data/input` directory
2. Run the main script:
```bash
python src/excel_processor.py
```

## Input File Requirements
- Excel files (.xlsx format)
- Each file should contain two columns:
  - en_US (English text)
  - Target language translation

## Output
- The script will generate a consolidated Excel file in the `data/output` directory
- The output filename includes a timestamp
- The output file will contain all translations merged by the English text

### Preserving literal values like `None` and `N/A`
When reading Excel files pandas can treat certain strings as missing values.
The loader uses `keep_default_na=False` so cells containing strings such as
`None` or `N/A` remain exactly as typed instead of becoming empty cells.

## Error Handling
- The script includes comprehensive error handling and logging
- Logs are stored in the `logs` directory 