# 🌍 GREENFIN-AI
End-to-End Financed Emissions and Climate Risk Analytics Platform

## Overview
GREENFIN-AI models and visualizes financed emissions for financial portfolios using real-world ESG, financial, and loan data.

### Features (to be built)
- Data ingestion and ETL using Python + SQL
- Financed emissions modeling
- Climate stress testing
- Streamlit dashboard
- Docker + Jenkins CI/CD pipeline

### Folder Structure
See `/src` for code modules, `/data` for datasets, and `/db` for local database.

### Run Setup
```bash
pip install -r requirements.txt
python src/utils/db_utils.py
python src/ingestion/data_ingestor.py
python src/etl/data_cleaner.py
