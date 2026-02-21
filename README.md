# DailyPaper
AI Hackathon

# 사용 방법  
(1) 분석하기  
```python
# Option1. 어제자 주목받았던 논문
PYTHONPATH=src python -m dailypaper.cli run-yesterday
# Option2. 날짜 지정(YYYY-MM-DD) 형식 꼭 지키기
PYTHONPATH=src python -m dailypaper.cli run 2026-02-20
```

(2) Streamlit 실행
```python
streamlit run app.py
```
