import os
import streamlit as st
from openai import OpenAI
import json
import requests
import urllib.parse

# Load API key securely
os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
client = OpenAI() 

st.set_page_config(page_title="AI BPMN Swimlane Generator", page_icon="🛠", layout="wide")
st.title(" AI BPMN Swimlane Generator")
st.write("Paste workflow text, and AI will generate a BPMN diagram using PlantUML.")

# Input workflow text
workflow_text = st.text_area(" Enter Workflow Description", height=200,
                             placeholder="E.g., Customer places an order, System validates payment, Warehouse ships order...")

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

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )
        json_text = response.choices[0].message.content.strip()

        try:
            workflow_data = json.loads(json_text)
        except json.JSONDecodeError:
            st.error("❌ Failed to parse AI response as JSON.")
            st.code(json_text)
            st.stop()

    st.subheader("✅ Extracted Workflow JSON")
    st.json(workflow_data)

    # --- JSON → PlantUML BPMN with Swimlanes ---
    def json_to_plantuml(data):
        actors = data.get("actors", [])
        steps = data.get("steps", [])

        plantuml_lines = ["@startuml", "!include <bpmn>", ""]

        # Create one pool with lanes for each actor
        plantuml_lines.append("pool Process {")
        for actor in actors:
            plantuml_lines.append(f"  lane {actor} {{")
            # Add steps belonging to this actor
            for i, step in enumerate(steps):
                if step["actor"] == actor:
                    step_type = step.get("type", "task").lower()
                    action = step.get("action", "")
                    node_id = f"{actor}_{i}"

                    if step_type == "start":
                        plantuml_lines.append(f"    start event {node_id} : {action}")
                    elif step_type == "end":
                        plantuml_lines.append(f"    end event {node_id} : {action}")
                    elif step_type == "gateway":
                        plantuml_lines.append(f"    gateway {node_id} : {action}")
                    else:
                        plantuml_lines.append(f"    task {node_id} : {action}")
            plantuml_lines.append("  }")
        plantuml_lines.append("}")

        # Add simple sequential flow (linear for now)
        ids = [f"{s['actor']}_{i}" for i, s in enumerate(steps)]
        for a, b in zip(ids, ids[1:]):
            plantuml_lines.append(f"{a} --> {b}")

        plantuml_lines.append("@enduml")
        return "\n".join(plantuml_lines)

    plantuml_code = json_to_plantuml(workflow_data)

    st.subheader("📄 Generated PlantUML Code")
    st.code(plantuml_code, language="plantuml")

    # --- Render Diagram via PlantUML server ---
    def render_plantuml(uml_code: str):
        encoded = urllib.parse.quote(uml_code)
        server_url = f"http://www.plantuml.com/plantuml/svg/{encoded}"
        return server_url

    image_url = render_plantuml(plantuml_code)

    st.subheader("📊 BPMN Swimlane Diagram")
    st.image(image_url)

    st.download_button(
        label="📥 Download PlantUML Code",
        data=plantuml_code,
        file_name="workflow_bpmn_swimlanes.puml",
        mime="text/plain"
    )



