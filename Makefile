install:
	pip install -r requirements.txt

run:
	uvicorn src.main:app --reload