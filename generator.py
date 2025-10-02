import os
import streamlit as st
import openai
import json
import requests
import urllib.parse
import zlib
import base64


openai.api_key = st.secrets["OPENAI_API_KEY"]



st.set_page_config(page_title="AI BPMN Swimlane Generator", page_icon="🛠", layout="wide")
st.title(" AI BPMN Swimlane Generator")
st.write("Paste workflow text, and AI will generate a BPMN diagram using PlantUML.")

# Input workflow text
workflow_text = st.text_area(" Enter Workflow Description", height=200,
                             placeholder="E.g., Customer places an order, System validates payment, Warehouse ships order...")

# --- PlantUML Encoding Helpers ---
def plantuml_encode(text: str) -> str:
    """Compress + encode PlantUML for server rendering"""
    zlibbed_str = zlib.compress(text.encode("utf-8"))[2:-4]
    encoded = base64.b64encode(zlibbed_str).decode("utf-8")
    trans = str.maketrans(
        'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/',
        '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_'
    )
    return encoded.translate(trans)

def render_plantuml(uml_code: str) -> str:
    encoded = plantuml_encode(uml_code)
    return f"http://www.plantuml.com/plantuml/svg/{encoded}"

# --- JSON → PlantUML ---
def json_to_plantuml(data):
    actors = data.get("actors", [])
    steps = data.get("steps", [])

    # Ensure actors include all step actors
    for s in steps:
        if s["actor"] not in actors:
            actors.append(s["actor"])

    plantuml_lines = ["@startuml", "!include <bpmn>", ""]

    plantuml_lines.append("pool Process {")
    for actor in actors:
        plantuml_lines.append(f"  lane {actor} {{")
        for i, step in enumerate(steps):
            if step["actor"] == actor:
                step_type = step.get("type", "task").lower()
                action = step.get("action", "")
                node_id = f"{actor}_{i}".replace(" ", "_")

                if step_type == "start":
                    plantuml_lines.append(f"    start {node_id} : {action}")
                elif step_type == "end":
                    plantuml_lines.append(f"    end {node_id} : {action}")
                elif step_type == "gateway":
                    plantuml_lines.append(f"    gateway {node_id} : {action}")
                else:
                    plantuml_lines.append(f"    task {node_id} : {action}")
        plantuml_lines.append("  }")
    plantuml_lines.append("}")

    # Sequential flow
    ids = [f"{s['actor']}_{i}".replace(" ", "_") for i, s in enumerate(steps)]
    for a, b in zip(ids, ids[1:]):
        plantuml_lines.append(f"{a} --> {b}")

    plantuml_lines.append("@enduml")
    return "\n".join(plantuml_lines)

# --- Main ---
if st.button("Generate BPMN Diagram") and workflow_text.strip():
    with st.spinner("Parsing workflow into structured JSON..."):
        prompt = f"""
        Convert the following workflow into structured JSON for BPMN diagramming.
        Use format:
        {{
          "actors": ["Actor1", "Actor2"],
          "steps": [
            {{"actor": "Actor1", "action": "Start Event", "type": "start"}},
            {{"actor": "Actor1", "action": "Task Name", "type": "task"}},
            {{"actor": "Actor2", "action": "Gateway Condition?", "type": "gateway"}},
            {{"actor": "Actor2", "action": "End Event", "type": "end"}}
          ]
        }}

        Workflow:
        {workflow_text}
        """

        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )
        json_text = response.choices[0].message["content"].strip()
        if json_text.startswith("```"):
            json_text = json_text.strip("`")   # remove backticks
            if json_text.lower().startswith("json"):
                json_text = json_text[4:].strip()

        try:
            workflow_data = json.loads(json_text)
        except json.JSONDecodeError:
            st.error("❌ Failed to parse AI response as JSON.")
            st.code(json_text)
            st.stop()

    st.subheader("✅ Extracted Workflow JSON")
    st.json(workflow_data)

    # Convert JSON → PlantUML
    plantuml_code = json_to_plantuml(workflow_data)

    st.subheader("📄 Generated PlantUML Code")
    st.code(plantuml_code, language="plantuml")

    # Render diagram
    image_url = render_plantuml(plantuml_code)

    st.subheader("📊 BPMN Swimlane Diagram")
    st.image(image_url)

    st.download_button(
        label="📥 Download PlantUML Code",
        data=plantuml_code,
        file_name="workflow_bpmn_swimlanes.puml",
        mime="text/plain"
    )



