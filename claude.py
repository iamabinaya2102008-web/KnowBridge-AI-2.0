import json
import re
from urllib.parse import quote
import requests
import streamlit as st
import networkx as nx
from pyvis.network import Network
import streamlit.components.v1 as components
from google import genai

st.set_page_config(page_title="KnowBridge AI 2.0", page_icon="🌐", layout="wide")

# ----------------------------------------------------------------------------
# Styling
# ----------------------------------------------------------------------------
COLORS = {
    "Computer Science": "#38BDF8",
    "Agriculture": "#4ADE80",
    "Engineering": "#FACC15",
    "Environmental Science": "#C084FC",
    "Biology": "#FB7185",
    "Economics": "#FB923C",
    "Urban Planning": "#2DD4BF",
}
DEFAULT_COLOR = "#CBD5E1"

st.markdown("""
<style>
.stApp { background: radial-gradient(circle at 15% 0%, #1e1b4b 0%, #0b1020 45%, #070b16 100%); }
.hero { padding: 1.6rem 2rem; border-radius: 20px; margin-bottom: 1.2rem;
        background: linear-gradient(120deg, rgba(99,102,241,.35), rgba(20,184,166,.25));
        border: 1px solid rgba(255,255,255,.12); }
.hero h1 { margin: 0; font-size: 2.4rem; color: #f8fafc; letter-spacing: -.5px; }
.hero p  { margin: .3rem 0 0; color: #cbd5e1; font-size: 1.05rem; }
.hero small { color: #94a3b8; }
.card { background: rgba(255,255,255,.05); border: 1px solid rgba(255,255,255,.1);
        border-radius: 14px; padding: 1rem 1.2rem; margin-bottom: .8rem; }
.card h4 { margin: 0 0 .3rem; color: #f1f5f9; }
.card p  { margin: 0; color: #cbd5e1; font-size: .93rem; }
.pill { display:inline-block; padding: 2px 10px; border-radius: 999px; font-size: .75rem;
        font-weight: 600; color: #0b1020; margin: 0 6px 6px 0; }
.metric { text-align:center; padding: 1rem; border-radius: 14px;
          background: rgba(255,255,255,.06); border: 1px solid rgba(255,255,255,.1); }
.metric b { display:block; font-size: 1.9rem; color:#a5b4fc; }
.metric span { color:#94a3b8; font-size:.85rem; }
.gap { border-left: 4px solid #f59e0b; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
@keyframes flow { 0% {background-position: 0% 50%;} 50% {background-position: 100% 50%;} 100% {background-position: 0% 50%;} }
.stApp { background: linear-gradient(135deg, #0f0c29 0%, #1b1464 35%, #0b3d5c 70%, #0a2e2a 100%); background-attachment: fixed; }
section[data-testid="stSidebar"] { background: linear-gradient(180deg, #2e1065 0%, #1e3a8a 60%, #0f766e 100%); }
.hero { background: linear-gradient(120deg, #ec4899, #8b5cf6, #3b82f6, #06b6d4, #10b981);
        background-size: 300% 300%; animation: flow 10s ease infinite;
        border: none; box-shadow: 0 10px 40px rgba(139,92,246,.45); }
.hero h1 { color: #fff; text-shadow: 0 2px 12px rgba(0,0,0,.35); }
.hero p { color: #fff; font-weight: 500; }
.hero small { color: #f1f5f9; }
div.stButton > button[kind="primary"] { background: linear-gradient(90deg, #ec4899, #8b5cf6, #06b6d4);
        border: none; color: #fff; font-weight: 700; border-radius: 12px; padding: .7rem 1rem;
        box-shadow: 0 6px 20px rgba(236,72,153,.4); transition: transform .15s; }
div.stButton > button[kind="primary"]:hover { transform: translateY(-2px) scale(1.01); }
.metric { border: none; color: #fff; box-shadow: 0 6px 18px rgba(0,0,0,.3); }
.metric b { color: #fff; font-size: 2.1rem; }
.metric span { color: rgba(255,255,255,.9); font-weight: 500; }
.m-concepts { background: linear-gradient(135deg, #6366f1, #8b5cf6); }
.m-relationships { background: linear-gradient(135deg, #06b6d4, #3b82f6); }
.m-disciplines { background: linear-gradient(135deg, #10b981, #84cc16); }
.m-potentially { background: linear-gradient(135deg, #f59e0b, #ef4444); }
.card { transition: transform .15s, box-shadow .15s; border-left: 5px solid #8b5cf6; }
.card:hover { transform: translateY(-2px); box-shadow: 0 8px 22px rgba(0,0,0,.35); }
.card h4 { color: #fff; }
.card a { color: #7dd3fc; text-decoration: none; }
.gap { border-left: 5px solid #f59e0b; background: rgba(245,158,11,.10); }
.pill { box-shadow: 0 2px 8px rgba(0,0,0,.25); }
button[data-baseweb="tab"] { font-weight: 600; font-size: 1rem; }
button[data-baseweb="tab"][aria-selected="true"] { color: #f0abfc; }
div[data-baseweb="tab-highlight"] { background: linear-gradient(90deg, #ec4899, #06b6d4); height: 3px; }
</style>
<div class="hero">
  <h1>🌐 KnowBridge AI 2.0</h1>
  <p>Enter a topic. Discover knowledge. Connect disciplines.</p>
  <small>A prototype for discovering concepts and relationships across academic disciplines.</small>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.header("Demo settings")
    api_key = st.text_input("Gemini API key", type="password",
                            help="Enter your own key for this session. Do not share or commit it.")
    model_name = st.text_input("Gemini model", value="gemini-3.8-flash",
                               help="Change this if the model name is unavailable for your key.")
    expand = st.checkbox("Auto-expand coverage gaps (Gemini mode)", value=True,
                         help="Searches Wikipedia for under-covered subtopics and adds them to the graph.")
    st.caption("If no key is entered, the app uses a clearly labelled predefined sample-data mode. "
               "Samples available: Smart Agriculture and Renewable Energy in Smart Cities.")
    st.divider()
    st.caption("Prototype note: Wikipedia is the information source in this version. The coverage check only compares retrieved concepts with AI-suggested subtopics.")


# ----------------------------------------------------------------------------
# Wikipedia REST API
# ----------------------------------------------------------------------------
HEADERS = {"User-Agent": "KnowBridgeAIStudentPrototype/1.0 (educational demo)"}


@st.cache_data(show_spinner=False, ttl=3600)
def fetch_wikipedia(query, limit=5):
    search_url = "https://en.wikipedia.org/w/rest.php/v1/search/page"
    response = requests.get(search_url, params={"q": query, "limit": limit},
                            headers=HEADERS, timeout=15)
    response.raise_for_status()
    hits = response.json().get("pages", [])
    documents = []
    for hit in hits[:limit]:
        title = hit.get("title", "")
        key = hit.get("key") or title.replace(" ", "_")
        summary_url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + quote(key, safe="")
        try:
            page = requests.get(summary_url, headers=HEADERS, timeout=12)
            page.raise_for_status()
            data = page.json()
            extract = data.get("extract", "")
            page_url = data.get("content_urls", {}).get("desktop", {}).get(
                "page", "https://en.wikipedia.org/wiki/" + quote(key, safe=""))
            if extract:
                documents.append({"title": data.get("title", title), "text": extract, "url": page_url})
        except requests.RequestException:
            continue
    return documents


# ----------------------------------------------------------------------------
# Predefined sample data (no API key needed)
# ----------------------------------------------------------------------------
def normalize(value):
    return re.sub(r"[^a-z0-9]+", "", value.lower())


SAMPLE_TOPICS = {
    "Smart Agriculture": {
        "aliases": ["smartagriculture", "smartfarming"],
        "concepts": [
            {"name": "Smart Agriculture", "discipline": "Agriculture", "description": "Use of technology and data to improve farming decisions."},
            {"name": "IoT Sensors", "discipline": "Computer Science", "description": "Connected sensors collect field data such as temperature and soil moisture."},
            {"name": "Soil Moisture Monitoring", "discipline": "Agriculture", "description": "Measuring water content in soil to guide irrigation."},
            {"name": "Data Analytics", "discipline": "Computer Science", "description": "Analysing collected farm data to support decisions."},
            {"name": "Smart Irrigation", "discipline": "Engineering", "description": "Automating water delivery based on sensor readings and control systems."},
            {"name": "Water Conservation", "discipline": "Environmental Science", "description": "Reducing unnecessary water use in agriculture."},
        ],
        "relationships": [
            {"source": "Smart Agriculture", "target": "IoT Sensors", "relation": "uses"},
            {"source": "IoT Sensors", "target": "Soil Moisture Monitoring", "relation": "enable"},
            {"source": "Soil Moisture Monitoring", "target": "Smart Irrigation", "relation": "guides"},
            {"source": "IoT Sensors", "target": "Data Analytics", "relation": "provide data for"},
            {"source": "Data Analytics", "target": "Smart Irrigation", "relation": "supports"},
            {"source": "Smart Irrigation", "target": "Water Conservation", "relation": "can support"},
        ],
        "expected_subtopics": ["IoT Sensors", "Soil Moisture Monitoring", "Smart Irrigation",
                               "Data Analytics", "Water Conservation", "Crop Disease Detection"],
    },
    "Renewable Energy in Smart Cities": {
        "aliases": ["renewableenergyinsmartcities", "renewableenergysmartcities"],
        "concepts": [
            {"name": "Smart Cities", "discipline": "Urban Planning", "description": "Urban areas that use data and connected technology to manage resources and services more efficiently."},
            {"name": "Renewable Energy", "discipline": "Environmental Science", "description": "Energy from sources such as solar and wind that are naturally replenished."},
            {"name": "Solar Photovoltaics", "discipline": "Engineering", "description": "Panels that convert sunlight into electricity, often installed on rooftops and public buildings."},
            {"name": "Smart Grid", "discipline": "Engineering", "description": "An electricity network that uses sensing and control to balance supply and demand."},
            {"name": "IoT Smart Meters", "discipline": "Computer Science", "description": "Connected meters that report energy use in near real time."},
            {"name": "Energy Analytics", "discipline": "Computer Science", "description": "Analysing consumption and generation data to forecast demand and guide decisions."},
            {"name": "Energy Storage", "discipline": "Engineering", "description": "Batteries and other systems that store surplus renewable power for later use."},
            {"name": "Demand Response", "discipline": "Economics", "description": "Using prices or incentives to shift electricity use away from peak periods."},
            {"name": "Carbon Emission Reduction", "discipline": "Environmental Science", "description": "Lowering greenhouse gas emissions from city energy use."},
        ],
        "relationships": [
            {"source": "Smart Cities", "target": "Renewable Energy", "relation": "adopt"},
            {"source": "Renewable Energy", "target": "Solar Photovoltaics", "relation": "includes"},
            {"source": "Solar Photovoltaics", "target": "Smart Grid", "relation": "feeds power into"},
            {"source": "IoT Smart Meters", "target": "Energy Analytics", "relation": "provide data for"},
            {"source": "Energy Analytics", "target": "Smart Grid", "relation": "supports"},
            {"source": "Smart Grid", "target": "Energy Storage", "relation": "coordinates"},
            {"source": "Smart Grid", "target": "Demand Response", "relation": "enables"},
            {"source": "Demand Response", "target": "Carbon Emission Reduction", "relation": "can support"},
            {"source": "Energy Storage", "target": "Carbon Emission Reduction", "relation": "can support"},
            {"source": "Smart Cities", "target": "IoT Smart Meters", "relation": "deploy"},
        ],
        "expected_subtopics": ["Solar Photovoltaics", "Smart Grid", "IoT Smart Meters", "Energy Storage",
                               "Demand Response", "Carbon Emission Reduction", "Microgrids",
                               "Electric Vehicle Charging Integration", "Energy Equity and Access"],
    },
}


def find_sample_key(topic):
    """Return the name of the predefined sample matching the topic, or None."""
    n = normalize(topic)
    for name, sample in SAMPLE_TOPICS.items():
        if n == normalize(name) or n in sample["aliases"]:
            return name
    return None


def sample_data(topic):
    # Transparent fallback for rehearsed demonstrations of the predefined samples.
    sample = SAMPLE_TOPICS[find_sample_key(topic)]
    return {
        "concepts": [dict(c) for c in sample["concepts"]],
        "relationships": [dict(r) for r in sample["relationships"]],
        "expected_subtopics": list(sample["expected_subtopics"]),
    }


def extract_with_gemini(topic, documents, key, model, focus=None):
    client = genai.Client(api_key=key)
    source_text = "\n\n".join(
        f"Source: {d['title']}\nText: {d['text'][:1800]}" for d in documents
    )
    focus_line = f"Pay special attention to this subtopic: {focus}\n" if focus else ""
    prompt = f"""
You are helping build an educational cross-disciplinary knowledge graph.
Topic: {topic}
{focus_line}Use ONLY the source text below for factual concept descriptions and relationships.
Return valid JSON with exactly these top-level keys:
- concepts: array of objects with name, discipline, description
- relationships: array of objects with source, target, relation
- expected_subtopics: array of short strings representing useful subtopics to check for coverage
Use 5 to 10 concepts, 5 to 12 relationships. Disciplines may include Computer Science,
Engineering, Agriculture, Environmental Science, Biology, Economics, or other suitable fields.
Every relationship source and target must exactly match a concept name.
Do not claim that missing subtopics are missing from all scientific knowledge.
Source text:
{source_text}
"""
    result = client.models.generate_content(
        model=model,
        contents=prompt,
        config={"response_mime_type": "application/json"},
    )
    text = re.sub(r"^```(?:json)?|```$", "", (result.text or "").strip(), flags=re.M).strip()
    return json.loads(text)


def find_gaps(concepts, expected):
    names = [normalize(c.get("name", "")) for c in concepts]
    gaps = []
    for item in expected:
        n = normalize(item)
        if not n:
            continue
        if not any(n == x or n in x or x in n for x in names if x):
            gaps.append(item)
    return gaps


def merge(base, new):
    seen = {normalize(c.get("name", "")) for c in base["concepts"]}
    for c in new.get("concepts", []):
        if c.get("name") and normalize(c["name"]) not in seen:
            base["concepts"].append(c)
            seen.add(normalize(c["name"]))
    pairs = {(r.get("source"), r.get("target")) for r in base["relationships"]}
    for r in new.get("relationships", []):
        if (r.get("source"), r.get("target")) not in pairs:
            base["relationships"].append(r)


def pill(discipline):
    color = COLORS.get(discipline, DEFAULT_COLOR)
    return f'<span class="pill" style="background:{color}">{discipline}</span>'


# ----------------------------------------------------------------------------
# UI
# ----------------------------------------------------------------------------
CUSTOM_OPTION = "Custom topic"

if "topic" not in st.session_state:
    st.session_state["topic"] = "Smart Agriculture"


def on_sample_change():
    choice = st.session_state.get("sample_choice", CUSTOM_OPTION)
    if choice != CUSTOM_OPTION:
        st.session_state["topic"] = choice


st.selectbox(
    "📚 Predefined sample topics (work without an API key)",
    [CUSTOM_OPTION] + list(SAMPLE_TOPICS.keys()),
    index=1,
    key="sample_choice",
    on_change=on_sample_change,
    help="Pick a predefined sample to fill in the topic box, or choose 'Custom topic' and type your own.",
)
topic = st.text_input("🔎 Enter a topic", key="topic")
run = st.button("Discover Knowledge", type="primary", use_container_width=True)

if run:
    if not topic.strip():
        st.warning("Please enter a topic.")
        st.stop()

    sample_key = find_sample_key(topic)
    use_sample = (not api_key.strip()) and sample_key is not None

    try:
        docs = []
        try:
            with st.spinner("Retrieving public information from Wikipedia..."):
                docs = fetch_wikipedia(topic)
        except requests.RequestException as e:
            if not use_sample:
                raise
            st.info(f"Wikipedia could not be reached ({e}). The predefined sample still works offline; the Sources tab will be empty.")

        if not docs and not use_sample:
            st.error("No Wikipedia summaries were retrieved. Try a broader topic or check your internet connection.")
            st.stop()

        expanded = []
        if api_key.strip():
            with st.spinner("Gemini is extracting concepts and relationships..."):
                data = extract_with_gemini(topic, docs, api_key.strip(), model_name.strip())
            data.setdefault("concepts", [])
            data.setdefault("relationships", [])
            data.setdefault("expected_subtopics", [])
            mode = "Gemini AI"

            if expand:
                gaps_first = find_gaps(data["concepts"], data["expected_subtopics"])
                if gaps_first:
                    with st.spinner(f"Expanding knowledge for {min(len(gaps_first), 3)} under-covered subtopics..."):
                        for gap in gaps_first[:3]:
                            extra = fetch_wikipedia(f"{gap} {topic}", 2)
                            if not extra:
                                continue
                            try:
                                new = extract_with_gemini(topic, extra, api_key.strip(),
                                                          model_name.strip(), focus=gap)
                                merge(data, new)
                                expanded.append(gap)
                                for d in extra:
                                    if d["url"] not in {x["url"] for x in docs}:
                                        docs.append(d)
                            except Exception:
                                continue
            st.success("AI extraction completed using Gemini.")
        elif use_sample:
            data = sample_data(topic)
            st.info(f"Predefined sample data: the graph below is a prepared demonstration for "
                    f"\"{sample_key}\", not a live Gemini result. Add a Gemini API key in the sidebar to run AI extraction.")
            mode = f"Predefined sample data ({sample_key})"
        else:
            st.warning("Enter a Gemini API key to extract concepts for this topic. "
                       "Predefined sample data is available for: " + ", ".join(SAMPLE_TOPICS.keys()) + ".")
            st.stop()

        concepts = data.get("concepts", [])
        relationships = data.get("relationships", [])
        expected = data.get("expected_subtopics", [])

        valid_names = {c.get("name", "").strip() for c in concepts if c.get("name")}
        relationships = [
            r for r in relationships
            if r.get("source") in valid_names and r.get("target") in valid_names
        ]
        gaps = find_gaps(concepts, expected)
        disciplines = sorted({c.get("discipline", "Other") for c in concepts})

        # Metric cards
        cols = st.columns(4)
        for col, (num, label) in zip(cols, [
            (len(concepts), "Concepts"), (len(relationships), "Relationships"),
            (len(disciplines), "Disciplines"), (len(gaps), "Potentially under-covered"),
        ]):
            col.markdown(f'<div class="metric m-{label.split()[0].lower()}"><b>{num}</b><span>{label}</span></div>',
                         unsafe_allow_html=True)
        st.caption(f"Processing mode: {mode}")
        st.write("")

        tab_graph, tab_concepts, tab_gaps, tab_sources = st.tabs(
            ["🕸️ Knowledge graph", "💡 Concepts", "🧩 Coverage check", "📖 Sources"])

        # --- Graph ---
        with tab_graph:
            if use_sample:
                st.caption("📌 Predefined sample data — not generated live by an AI model.")
            st.markdown("".join(pill(d) for d in disciplines), unsafe_allow_html=True)
            graph = nx.DiGraph()
            for c in concepts:
                graph.add_node(c["name"], discipline=c.get("discipline", "Other"),
                               description=c.get("description", ""))
            for r in relationships:
                graph.add_edge(r["source"], r["target"], relation=r.get("relation", "related to"))

            if graph.number_of_nodes():
                net = Network(height="560px", width="100%", directed=True,
                              bgcolor="#0b1020", font_color="white", notebook=False)
                for node, attrs in graph.nodes(data=True):
                    discipline = attrs.get("discipline", "Other")
                    net.add_node(node, label=node,
                                 title=f"{node}\nDiscipline: {discipline}\n{attrs.get('description', '')}",
                                 color={"background": COLORS.get(discipline, DEFAULT_COLOR),
                                        "border": "#ffffff",
                                        "highlight": {"background": "#ffffff", "border": COLORS.get(discipline, DEFAULT_COLOR)}},
                                 size=28, borderWidth=3, shadow=True,
                                 font={"size": 16, "color": "#ffffff"})
                for source, target, attrs in graph.edges(data=True):
                    net.add_edge(source, target, label=attrs.get("relation", "related to"),
                                 title=attrs.get("relation", "related to"),
                                 color="rgba(255,255,255,.55)", width=2)
                net.set_options("""{"physics":{"barnesHut":{"gravitationalConstant":-9000,"springLength":150}},
                    "edges":{"font":{"size":10,"color":"#94a3b8","strokeWidth":0}},
                    "interaction":{"hover":true,"tooltipDelay":80}}""")
                components.html(net.generate_html(), height=580, scrolling=True)
                st.caption("Each circle is a concept (node); each arrow is a relationship (edge). Colours distinguish disciplines. Hover for descriptions.")
                st.download_button("⬇️ Download graph data (JSON)",
                                   json.dumps({"concepts": concepts, "relationships": relationships}, indent=2),
                                   file_name="knowledge_graph.json", mime="application/json")

        # --- Concepts ---
        with tab_concepts:
            if use_sample:
                st.caption("📌 Predefined sample data — not generated live by an AI model.")
            for c in sorted(concepts, key=lambda x: x.get("discipline", "")):
                st.markdown(
                    f'<div class="card" style="border-left-color:{COLORS.get(c.get("discipline", "Other"), DEFAULT_COLOR)}">{pill(c.get("discipline", "Other"))}'
                    f'<h4>{c.get("name", "")}</h4><p>{c.get("description", "")}</p></div>',
                    unsafe_allow_html=True)

        # --- Gaps ---
        with tab_gaps:
            if use_sample:
                st.caption("📌 Predefined sample data — these gaps are part of the prepared demonstration.")
            if expanded:
                st.success("Knowledge expanded with extra Wikipedia sources for: " + ", ".join(expanded))
            if gaps:
                st.write("Subtopics not directly represented among the extracted concept names:")
                for item in gaps:
                    note = ("Not included in this predefined sample's concepts — a direction for further learning."
                            if use_sample else
                            "Not sufficiently covered by the retrieved sources — a direction for further learning.")
                    st.markdown(f'<div class="card gap"><h4>{item}</h4><p>{note}</p></div>',
                                unsafe_allow_html=True)
            else:
                st.info("All suggested subtopics have a matching concept name.")
            st.caption("This is a basic prototype check against AI-suggested subtopics and retrieved sources. It does not prove a gap in all scientific knowledge.")

        # --- Sources ---
        with tab_sources:
            if use_sample:
                st.caption("Concepts above are predefined sample data. The Wikipedia pages below are the live search results for this topic, shown for further reading.")
            if not docs:
                st.info("No Wikipedia sources are available for this run.")
            for doc in docs:
                st.markdown(
                    f'<div class="card"><h4><a href="{doc["url"]}" target="_blank">{doc["title"]}</a></h4>'
                    f'<p>{doc["text"][:260]}…</p></div>', unsafe_allow_html=True)

    except requests.RequestException as e:
        st.error(f"Wikipedia retrieval failed: {e}")
    except json.JSONDecodeError:
        st.error("Gemini returned a response that could not be read as JSON. Try again.")
    except Exception as e:
        st.error(f"Something went wrong: {e}")
        st.caption("Check your API key, model name, internet connection, and installed packages.")

st.divider()
st.caption("KnowBridge AI 2.0 | Student prototype | Verify all AI-generated relationships before relying on them.")