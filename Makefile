load:
	python src/etl/loader.py

ratios:
	python src/ratios.py

test:
	pytest

report:
	python src/report.py

dashboard:
	streamlit run dashboard/app.py

api:
	python src/api.py

clean:
	del /s /q __pycache__