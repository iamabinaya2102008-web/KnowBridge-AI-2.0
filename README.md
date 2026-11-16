# KnowBridge AI 2.0 – Minimum Working Prototype

## What it demonstrates
- Topic input using Streamlit
- Wikipedia search and summary retrieval
- Gemini-based concept and relationship extraction (with an API key)
- NetworkX graph structure and PyVis interactive visualization
- Basic subtopic coverage comparison
- Source links

## Windows setup (VS Code)
1. Install Python if it is not already installed.
2. Extract this folder.
3. Open the folder in VS Code.
4. Open Terminal > New Terminal.
5. Run:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

If PowerShell blocks activation, you can skip activation and run:
```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Gemini API key
- Create/access a Gemini API key through Google's official AI Studio.
- Paste the key into the app's sidebar for the current session.
- Do not put the key directly into the Python source code or upload it to GitHub.
- If no key is entered, the app offers a clearly labelled prepared Smart Agriculture sample graph. This is a fallback demo, not live AI extraction.

## Demo suggestion
Use the topic `Smart Agriculture`. Show source summaries, extracted concepts, the interactive graph, and the coverage check. If using sample mode, clearly tell judges it is prepared sample data. For a genuine Gemini demonstration, enter a valid API key.

## Important
This is a prototype, not a validated research tool. AI-generated relationships and coverage suggestions need human verification. The basic coverage comparison checks whether a suggested subtopic matches an extracted concept name; it does not prove that a topic is absent from scientific knowledge.
