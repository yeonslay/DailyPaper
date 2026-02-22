# DailyPaper
AI Hackathon

# 사용 방법  
(1) 분석하기  
```bash
# Option1. 어제자 주목받았던 논문
PYTHONPATH=src python -m dailypaper.cli run-yesterday
# Option2. 날짜 지정(YYYY-MM-DD) 형식 꼭 지키기
PYTHONPATH=src python -m dailypaper.cli run 2026-02-20
```

(2) Streamlit 실행
```bash
streamlit run app.py
```

(3) 자동화 (화~토 매일 09:30)
```powershell
# Windows: 작업 스케줄러 등록 (한 번만 실행)
cd DailyPaper
powershell -ExecutionPolicy Bypass -File scripts\setup-scheduled-task.ps1
```
등록 후 매일 09:30에 실행되며, 화~토만 실제로 `run-yesterday`가 수행됨.  
주의사항! 절전모드 이상으로 해놓기!!
