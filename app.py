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

st.title("🌐 KnowBridge AI 2.0")
st.caption("Enter a topic. Discover knowledge. Connect disciplines.")
st.write("A prototype for discovering concepts and relationships across academic disciplines.")

with st.sidebar:
    st.header("Demo settings")
    api_key = st.text_input("Gemini API key", type="password",
                            help="Enter your own key for this session. Do not share or commit it.")
    st.caption("If no key is entered, the app uses a clearly labelled sample-data mode for the Smart Agriculture demo.")
    st.divider()
    st.caption("Prototype note: Wikipedia is the information source in this version. The coverage check only compares retrieved concepts with AI-suggested subtopics.")

def fetch_wikipedia(topic):
    headers = {"User-Agent": "KnowBridgeAIStudentPrototype/1.0 (educational demo)"}
    search_url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query", "list": "search", "srsearch": topic,
        "srlimit": 5, "format": "json"
    }
    response = requests.get(search_url, params=params, headers=headers, timeout=15)
    response.raise_for_status()
    hits = response.json().get("query", {}).get("search", [])
    documents = []
    for hit in hits[:5]:
        title = hit["title"]
        summary_url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + quote(title.replace(" ", "_"))
        try:
            page = requests.get(summary_url, headers=headers, timeout=12)
            page.raise_for_status()
            data = page.json()
            extract = data.get("extract", "")
            page_url = data.get("content_urls", {}).get("desktop", {}).get("page",
                        "https://en.wikipedia.org/wiki/" + quote(title.replace(" ", "_")))
            if extract:
                documents.append({"title": title, "text": extract, "url": page_url})
        except requests.RequestException:
            continue
    return documents

def sample_data(topic):
    # Transparent fallback for a rehearsed Smart Agriculture demonstration.
    concepts = [
        {"name": "Smart Agriculture", "discipline": "Agriculture", "description": "Use of technology and data to improve farming decisions."},
        {"name": "IoT Sensors", "discipline": "Computer Science", "description": "Connected sensors collect field data such as temperature and soil moisture."},
        {"name": "Soil Moisture Monitoring", "discipline": "Agriculture", "description": "Measuring water content in soil to guide irrigation."},
        {"name": "Data Analytics", "discipline": "Computer Science", "description": "Analysing collected farm data to support decisions."},
        {"name": "Smart Irrigation", "discipline": "Engineering", "description": "Automating water delivery based on sensor readings and control systems."},
        {"name": "Water Conservation", "discipline": "Environmental Science", "description": "Reducing unnecessary water use in agriculture."},
    ]
    relationships = [
        {"source": "Smart Agriculture", "target": "IoT Sensors", "relation": "uses"},
        {"source": "IoT Sensors", "target": "Soil Moisture Monitoring", "relation": "enable"},
        {"source": "Soil Moisture Monitoring", "target": "Smart Irrigation", "relation": "guides"},
        {"source": "IoT Sensors", "target": "Data Analytics", "relation": "provide data for"},
        {"source": "Data Analytics", "target": "Smart Irrigation", "relation": "supports"},
        {"source": "Smart Irrigation", "target": "Water Conservation", "relation": "can support"},
    ]
    return {
        "concepts": concepts,
        "relationships": relationships,
        "expected_subtopics": ["IoT Sensors", "Soil Moisture Monitoring", "Smart Irrigation",
                               "Data Analytics", "Water Conservation", "Crop Disease Detection"]
    }

def extract_with_gemini(topic, documents, key):
    client = genai.Client(api_key=key)
    source_text = "\n\n".join(
        f"Source: {d['title']}\nText: {d['text'][:1800]}"
        for d in documents
    )
    prompt = f"""
You are helping build an educational cross-disciplinary knowledge graph.
Topic: {topic}
Use ONLY the source text below for factual concept descriptions and relationships.
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
        model="gemini-3.8-flash",
        contents=prompt,
        config={"response_mime_type": "application/json"}
    )
    data = json.loads(result.text)
    return data

def normalize(value):
    return re.sub(r"[^a-z0-9]+", "", value.lower())

topic = st.text_input("Enter a topic", value="Smart Agriculture")
run = st.button("Discover Knowledge", type="primary", use_container_width=True)

if run:
    if not topic.strip():
        st.warning("Please enter a topic.")
        st.stop()

    try:
        with st.spinner("Retrieving public information from Wikipedia..."):
            docs = fetch_wikipedia(topic)
        if not docs:
            st.error("No Wikipedia summaries were retrieved. Try a broader topic or check your internet connection.")
            st.stop()

        st.subheader("1. Retrieved information")
        st.success(f"Retrieved {len(docs)} source summaries.")
        for doc in docs:
            with st.expander(doc["title"]):
                st.write(doc["text"])
                st.markdown(f"[Open source]({doc['url']})")

        if api_key.strip():
            with st.spinner("Gemini is extracting concepts and relationships..."):
                data = extract_with_gemini(topic, docs, api_key.strip())
            st.success("AI extraction completed using Gemini.")
            mode = "Gemini AI"
        elif normalize(topic) in ("smartagriculture", "smartfarming"):
            data = sample_data(topic)
            st.info("Sample-data mode: the graph below is a prepared demonstration, not a live Gemini result. Add a Gemini API key in the sidebar to run AI extraction.")
            mode = "Sample demonstration"
        else:
            st.warning("Enter a Gemini API key to extract concepts for this topic. Sample-data mode is available for Smart Agriculture.")
            st.stop()

        concepts = data.get("concepts", [])
        relationships = data.get("relationships", [])
        expected = data.get("expected_subtopics", [])

        valid_names = {c.get("name", "").strip() for c in concepts if c.get("name")}
        relationships = [
            r for r in relationships
            if r.get("source") in valid_names and r.get("target") in valid_names
        ]

        st.subheader("2. Extracted concepts")
        st.caption(f"Processing mode: {mode}")
        if concepts:
            st.dataframe(concepts, use_container_width=True, hide_index=True)

        st.subheader("3. Interactive knowledge graph")
        graph = nx.DiGraph()
        for c in concepts:
            graph.add_node(c["name"], discipline=c.get("discipline", "Other"))
        for r in relationships:
            graph.add_edge(r["source"], r["target"], relation=r.get("relation", "related to"))

        if graph.number_of_nodes():
            net = Network(height="560px", width="100%", directed=True,
                          bgcolor="#111827", font_color="white", notebook=False)
            colors = {
                "Computer Science": "#60A5FA",
                "Agriculture": "#34D399",
                "Engineering": "#FBBF24",
                "Environmental Science": "#A78BFA",
                "Biology": "#F472B6",
            }
            for node, attrs in graph.nodes(data=True):
                discipline = attrs.get("discipline", "Other")
                net.add_node(node, label=node, title=f"{node}\nDiscipline: {discipline}",
                             color=colors.get(discipline, "#CBD5E1"), size=24)
            for source, target, attrs in graph.edges(data=True):
                net.add_edge(source, target, label=attrs.get("relation", "related to"),
                             title=attrs.get("relation", "related to"))
            html = net.generate_html()
            components.html(html, height=580, scrolling=True)
            st.caption("Each circle is a concept (node); each arrow is a relationship (edge). Colours distinguish disciplines.")

        st.subheader("4. Knowledge coverage check")
        concept_names = {normalize(c.get("name", "")) for c in concepts}
        gaps = [item for item in expected if normalize(item) not in concept_names]
        col1, col2, col3 = st.columns(3)
        col1.metric("Concepts", len(concepts))
        col2.metric("Relationships", len(relationships))
        col3.metric("Potentially under-covered", len(gaps))
        if gaps:
            st.write("Subtopics not directly represented among the extracted concept names:")
            for item in gaps:
                st.write(f"• {item}")
        else:
            st.write("All suggested subtopics have a matching concept name.")
        st.caption("This is a basic prototype check against AI-suggested subtopics and retrieved sources. It does not prove a gap in all scientific knowledge.")

        st.subheader("5. Sources")
        for doc in docs:
            st.markdown(f"- [{doc['title']}]({doc['url']})")

    except requests.RequestException as e:
        st.error(f"Wikipedia retrieval failed: {e}")
    except json.JSONDecodeError:
        st.error("Gemini returned a response that could not be read as JSON. Try again.")
    except Exception as e:
        st.error(f"Something went wrong: {e}")
        st.caption("Check your API key, internet connection, and installed packages.")

st.divider()
st.caption("KnowBridge AI 2.0 | Student prototype | Verify all AI-generated relationships before relying on them.")
